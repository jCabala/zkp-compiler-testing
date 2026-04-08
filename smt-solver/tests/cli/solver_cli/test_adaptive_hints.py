"""
Unit tests for adaptive hints parameter tuning.

Tests cover:
1. _update_parameters — tuning logic (increase / decrease / no-op / caps / floors)
2. Schedule advancement — update_every doubling, prob_step decreasing
3. record_run — accumulation and triggered update at correct interval
"""

import pytest
from src.cli.solver_cli.adaptive_hints import (
    AdaptiveHintsState,
    _update_parameters,
    record_run,
    HINT_MODELS,
    HINT_PROBABILITY,
    INITIAL_UPDATE_EVERY,
    INITIAL_PROB_STEP,
    MAX_UPDATE_EVERY,
    MIN_PROB_STEP,
    MIN_PROBABILITY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(
    hint_models=HINT_MODELS,
    hint_probability=HINT_PROBABILITY,
    recent_times=None,
    total_runs=0,
    update_every=INITIAL_UPDATE_EVERY,
    prob_step=INITIAL_PROB_STEP,
    runs_since_last_update=0,
) -> AdaptiveHintsState:
    return AdaptiveHintsState(
        hint_models=hint_models,
        hint_probability=hint_probability,
        recent_times=recent_times or [],
        total_runs=total_runs,
        update_every=update_every,
        prob_step=prob_step,
        runs_since_last_update=runs_since_last_update,
    )


TIMEOUT = 30  # seconds, used throughout


# ---------------------------------------------------------------------------
# 1. _update_parameters — tuning logic
# ---------------------------------------------------------------------------

class TestUpdateParameters:

    # --- increase path (>10% over threshold) ---

    def test_increase_when_many_timeouts(self):
        # 2 out of 10 = 20% >= timeout → increase
        times = [35.0] * 2 + [10.0] * 8
        s = _state(hint_probability=0.5, recent_times=times, prob_step=0.1)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == pytest.approx(0.6)

    def test_increase_caps_at_1(self):
        times = [35.0] * 5 + [5.0] * 5  # 50% over
        s = _state(hint_probability=0.95, recent_times=times, prob_step=0.3)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == 1.0

    # --- decrease path (≤10% over threshold, avg < 0.8 * timeout) ---

    def test_decrease_when_solving_fast(self):
        # all solves fast, avg = 10s, ratio = 10/30 ≈ 0.33 < 0.8
        times = [10.0] * 10
        s = _state(hint_probability=0.5, recent_times=times, prob_step=0.1)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == pytest.approx(0.4)

    def test_decrease_floors_at_min_probability(self):
        times = [5.0] * 10
        s = _state(hint_probability=MIN_PROBABILITY + 0.02, recent_times=times, prob_step=0.3)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == pytest.approx(MIN_PROBABILITY)

    def test_increase_hint_models_when_already_at_floor(self):
        times = [5.0] * 10
        s = _state(hint_models=3, hint_probability=MIN_PROBABILITY, recent_times=times, prob_step=0.1)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_models == 4
        assert result.hint_probability == pytest.approx(MIN_PROBABILITY)

    # --- sweet spot (≤10% over threshold, 0.8 <= avg_ratio <= 1.0) ---

    def test_no_change_in_sweet_spot(self):
        # avg = 25s, ratio = 25/30 ≈ 0.83, no timeouts
        times = [25.0] * 10
        s = _state(hint_probability=0.6, recent_times=times)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == pytest.approx(0.6)
        assert result.hint_models == HINT_MODELS

    def test_no_change_when_avg_exactly_0_8(self):
        times = [24.0] * 10  # 24/30 = 0.8 exactly → no change
        s = _state(hint_probability=0.6, recent_times=times)
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == pytest.approx(0.6)

    # --- no solving_timeout set ---

    def test_no_change_without_timeout(self):
        times = [100.0] * 10  # would trigger increase if timeout was set
        s = _state(hint_probability=0.5, recent_times=times)
        result = _update_parameters(s, solving_timeout=None)
        assert result.hint_probability == pytest.approx(0.5)
        assert result.hint_models == HINT_MODELS

    def test_no_change_with_empty_recent_times(self):
        s = _state(hint_probability=0.5, recent_times=[])
        result = _update_parameters(s, TIMEOUT)
        assert result.hint_probability == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 2. Schedule advancement
# ---------------------------------------------------------------------------

class TestScheduleAdvancement:

    def test_update_every_doubles(self):
        s = _state(update_every=1, recent_times=[10.0])
        result = _update_parameters(s, TIMEOUT)
        assert result.update_every == 2

    def test_update_every_caps_at_max(self):
        s = _state(update_every=MAX_UPDATE_EVERY, recent_times=[10.0])
        result = _update_parameters(s, TIMEOUT)
        assert result.update_every == MAX_UPDATE_EVERY

    def test_prob_step_decreases(self):
        s = _state(prob_step=0.3, recent_times=[10.0])
        result = _update_parameters(s, TIMEOUT)
        assert result.prob_step == pytest.approx(0.25)

    def test_prob_step_floors_at_min(self):
        s = _state(prob_step=MIN_PROB_STEP, recent_times=[10.0])
        result = _update_parameters(s, TIMEOUT)
        assert result.prob_step == pytest.approx(MIN_PROB_STEP)

    def test_full_schedule_sequence(self):
        """update_every: 1→2→4→8→16→32→32; prob_step: 0.3→0.25→0.2→0.15→0.1→0.05→0.05"""
        s = _state(update_every=1, prob_step=0.3, recent_times=[10.0])
        expected_intervals = [2, 4, 8, 16, 32, 32]
        expected_steps = [0.25, 0.20, 0.15, 0.10, 0.05, 0.05]
        for interval, step in zip(expected_intervals, expected_steps):
            s = _update_parameters(s, TIMEOUT)
            s = _state(update_every=s.update_every, prob_step=s.prob_step, recent_times=[10.0])
            assert s.update_every == interval
            assert s.prob_step == pytest.approx(step)


# ---------------------------------------------------------------------------
# 3. record_run — accumulation and interval triggering
# ---------------------------------------------------------------------------

class TestRecordRun:

    def test_accumulates_times_before_update(self):
        # update_every=2: first run should NOT trigger update
        s = _state(update_every=2)
        s = record_run(s, elapsed_seconds=10.0, solving_timeout=TIMEOUT)
        assert s.recent_times == [10.0]
        assert s.runs_since_last_update == 1

    def test_triggers_update_at_interval(self):
        # update_every=2: second run triggers update, resets counters
        s = _state(update_every=2)
        s = record_run(s, elapsed_seconds=10.0, solving_timeout=TIMEOUT)
        s = record_run(s, elapsed_seconds=10.0, solving_timeout=TIMEOUT)
        assert s.recent_times == []
        assert s.runs_since_last_update == 0

    def test_update_every_1_triggers_on_first_run(self):
        s = _state(update_every=1)
        s = record_run(s, elapsed_seconds=10.0, solving_timeout=TIMEOUT)
        assert s.recent_times == []
        assert s.runs_since_last_update == 0

    def test_total_runs_increments(self):
        s = _state()
        s = record_run(s, elapsed_seconds=5.0)
        s = record_run(s, elapsed_seconds=5.0)
        assert s.total_runs == 2

    def test_parameters_change_after_update_triggered(self):
        # update_every=1, all solves fast → should decrease probability after first run
        s = _state(update_every=1, hint_probability=0.5, prob_step=0.1)
        s = record_run(s, elapsed_seconds=5.0, solving_timeout=TIMEOUT)
        assert s.hint_probability == pytest.approx(0.4)
