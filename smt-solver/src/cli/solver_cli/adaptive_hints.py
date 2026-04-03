"""
Adaptive hints: automatically tune HINT_MODELS and HINT_PROBABILITY
based on observed solve times across benchmarks.

State is persisted in tmp_dir/adaptive_hints_state.json so it accumulates
across multiple `solve` invocations (e.g. during a fuzzing session).

Schedule: parameters are updated after every `update_every` oracle runs.
  - update_every starts at 1 and doubles each update (1 → 2 → 4 → ... → 32, then fixed)
  - prob_step starts at 0.3 and decreases by 0.05 each update (→ 0.05, then fixed)

Strategy (applied when solving_timeout is set):
  over_threshold_ratio = fraction of recent solves with elapsed >= solving_timeout
  avg_ratio            = avg_recent_time / solving_timeout

  - over_threshold_ratio > 0.1  → too many timeouts: increase hint_probability by prob_step (cap 1.0)
  - over_threshold_ratio <= 0.1 (>=90% efficient):
      avg_ratio < 0.8           → solving fast: decrease hint_probability by prob_step (floor MIN_PROBABILITY);
                                   once at floor, increase hint_models by 1
      avg_ratio >= 0.8          → do nothing (in the sweet spot)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

# Initial values
HINT_MODELS = 5
HINT_PROBABILITY = 1.0
INITIAL_UPDATE_EVERY = 1
MAX_UPDATE_EVERY = 32
INITIAL_PROB_STEP = 0.3
MIN_PROB_STEP = 0.05
MIN_PROBABILITY = 0.1

STATE_FILE = "adaptive_hints_state.json"


@dataclass
class AdaptiveHintsState:
    hint_models: int
    hint_probability: float
    recent_times: list[float]
    total_runs: int
    update_every: int         # current update interval
    prob_step: float          # current step size for hint_probability
    runs_since_last_update: int


def _default_state() -> AdaptiveHintsState:
    return AdaptiveHintsState(
        hint_models=HINT_MODELS,
        hint_probability=HINT_PROBABILITY,
        recent_times=[],
        total_runs=0,
        update_every=INITIAL_UPDATE_EVERY,
        prob_step=INITIAL_PROB_STEP,
        runs_since_last_update=0,
    )


def load_state(tmp_dir: Path) -> AdaptiveHintsState:
    """Load adaptive hints state from tmp_dir, or return defaults if not found."""
    path = tmp_dir / STATE_FILE
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return AdaptiveHintsState(**data)
        except Exception:
            pass
    return _default_state()


def save_state(tmp_dir: Path, state: AdaptiveHintsState) -> None:
    """Persist adaptive hints state to tmp_dir."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / STATE_FILE
    path.write_text(json.dumps(asdict(state), indent=2))


def record_run(state: AdaptiveHintsState, elapsed_seconds: float, solving_timeout: int | None = None) -> AdaptiveHintsState:
    """Record the elapsed time of one oracle run and update parameters if due."""
    runs_since_last_update = state.runs_since_last_update + 1
    total_runs = state.total_runs + 1
    recent_times = state.recent_times + [elapsed_seconds]

    updated = AdaptiveHintsState(
        hint_models=state.hint_models,
        hint_probability=state.hint_probability,
        recent_times=recent_times,
        total_runs=total_runs,
        update_every=state.update_every,
        prob_step=state.prob_step,
        runs_since_last_update=runs_since_last_update,
    )

    if runs_since_last_update >= state.update_every:
        updated = _update_parameters(updated, solving_timeout)
        updated.recent_times = []
        updated.runs_since_last_update = 0

    return updated


def _update_parameters(state: AdaptiveHintsState, solving_timeout: int | None) -> AdaptiveHintsState:
    """
    Adjust hint_probability and hint_models based on avg recent solve time vs timeout.
    Also advances the update schedule (doubles update_every, decreases prob_step).
    No-ops on hint values if solving_timeout is not set.
    """
    hint_probability = state.hint_probability
    hint_models = state.hint_models

    if solving_timeout and state.recent_times:
        n = len(state.recent_times)
        over_threshold = sum(1 for t in state.recent_times if t >= solving_timeout) / n
        avg_time = sum(state.recent_times) / n
        avg_ratio = avg_time / solving_timeout

        if over_threshold > 0.1:
            hint_probability = min(1.0, hint_probability + state.prob_step)
        else:
            # >=90% efficient: use average to decide whether to decrease
            if avg_ratio < 0.8:
                if hint_probability > MIN_PROBABILITY:
                    hint_probability = max(MIN_PROBABILITY, hint_probability - state.prob_step)
                else:
                    hint_models += 1

    # Advance schedule
    new_update_every = min(state.update_every * 2, MAX_UPDATE_EVERY)
    new_prob_step = max(round(state.prob_step - 0.05, 10), MIN_PROB_STEP)

    return AdaptiveHintsState(
        hint_models=hint_models,
        hint_probability=round(hint_probability, 10),
        recent_times=state.recent_times,
        total_runs=state.total_runs,
        update_every=new_update_every,
        prob_step=new_prob_step,
        runs_since_last_update=state.runs_since_last_update,
    )
