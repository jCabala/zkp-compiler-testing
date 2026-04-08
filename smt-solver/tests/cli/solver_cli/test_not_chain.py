"""
Unit tests for NOT chain augmentation (not_chain.py).

Test groups:
1. augment_smt2       — injection correctness, variable naming, count sampling
2. compute_chain_hints — correct alternating values, missing anchor, large chains
3. Integration         — 1000-link chain hints computed correctly and quickly
"""

import re
import time
import random
import pytest
from src.cli.solver_cli.not_chain import (
    augment_smt2,
    compute_chain_hints,
    ALWAYS_HINT_PREFIX,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_FORMULA = """\
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(declare-fun x3 () Bool)
(assert (not x3))
(assert x1)
(assert (or (not x1) (not x2) x3))
(check-sat)
(get-model)
"""

CHAIN_LENGTH = 10  # short for most unit tests
LONG_CHAIN_LENGTH = 1000


# ---------------------------------------------------------------------------
# 1. augment_smt2
# ---------------------------------------------------------------------------

class TestAugmentSmt2:

    def test_no_chains_when_max_count_zero(self):
        rng = random.Random(42)
        augmented, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=0, rng=rng)
        assert chains == []
        assert augmented == SIMPLE_FORMULA

    def test_chain_count_within_bounds(self):
        rng = random.Random(0)
        for _ in range(20):
            _, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=3, rng=rng)
            assert 0 <= len(chains) <= 3

    def test_anchors_are_distinct(self):
        rng = random.Random(1)
        _, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=3, rng=rng)
        anchors = [a for a, _ in chains]
        assert len(anchors) == len(set(anchors))

    def test_anchors_are_existing_variables(self):
        rng = random.Random(2)
        _, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=3, rng=rng)
        for anchor, _ in chains:
            assert anchor in ("x1", "x2", "x3")

    def test_variables_declared_in_formula(self):
        rng = random.Random(3)
        augmented, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=2, rng=rng)
        for anchor, chain_idx in chains:
            for i in range(1, CHAIN_LENGTH + 1):
                var = f"{ALWAYS_HINT_PREFIX}{chain_idx}_{i}"
                assert f"(declare-fun {var} () Bool)" in augmented

    def test_assertions_injected_before_check_sat(self):
        rng = random.Random(4)
        augmented, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=1, rng=rng)
        check_sat_pos = augmented.index("(check-sat)")
        for anchor, chain_idx in chains:
            var1 = f"{ALWAYS_HINT_PREFIX}{chain_idx}_1"
            assert augmented.index(f"(assert (= {var1}") < check_sat_pos

    def test_first_link_anchored_to_existing_var(self):
        rng = random.Random(5)
        augmented, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=1, rng=rng)
        for anchor, chain_idx in chains:
            var1 = f"{ALWAYS_HINT_PREFIX}{chain_idx}_1"
            assert f"(assert (= {var1} (not {anchor})))" in augmented

    def test_chain_links_are_consecutive_nots(self):
        rng = random.Random(6)
        augmented, chains = augment_smt2(SIMPLE_FORMULA, CHAIN_LENGTH, max_count=1, rng=rng)
        for anchor, chain_idx in chains:
            for i in range(2, CHAIN_LENGTH + 1):
                vi = f"{ALWAYS_HINT_PREFIX}{chain_idx}_{i}"
                vi_prev = f"{ALWAYS_HINT_PREFIX}{chain_idx}_{i - 1}"
                assert f"(assert (= {vi} (not {vi_prev})))" in augmented

    def test_formula_without_xN_vars_returns_unchanged(self):
        formula = "(set-logic QF_BV)\n(assert true)\n(check-sat)\n"
        rng = random.Random(0)
        augmented, chains = augment_smt2(formula, CHAIN_LENGTH, max_count=5, rng=rng)
        assert chains == []
        assert augmented == formula


# ---------------------------------------------------------------------------
# 2. compute_chain_hints
# ---------------------------------------------------------------------------

class TestComputeChainHints:

    def test_anchor_true_first_link_is_false(self):
        chains = [("x1", 1)]
        hints = compute_chain_hints({"x1": True}, chains, chain_length=1)
        assert hints[f"{ALWAYS_HINT_PREFIX}1_1"] is False

    def test_anchor_false_first_link_is_true(self):
        chains = [("x1", 1)]
        hints = compute_chain_hints({"x1": False}, chains, chain_length=1)
        assert hints[f"{ALWAYS_HINT_PREFIX}1_1"] is True

    def test_values_alternate(self):
        chains = [("x1", 1)]
        hints = compute_chain_hints({"x1": True}, chains, chain_length=6)
        expected = [False, True, False, True, False, True]
        for i, exp in enumerate(expected, start=1):
            assert hints[f"{ALWAYS_HINT_PREFIX}1_{i}"] is exp

    def test_missing_anchor_skipped(self):
        chains = [("x1", 1), ("x2", 2)]
        hints = compute_chain_hints({"x1": True}, chains, chain_length=3)
        # x2 anchor missing — chain 2 should not appear
        assert all(k.startswith(f"{ALWAYS_HINT_PREFIX}1_") for k in hints)
        assert not any(k.startswith(f"{ALWAYS_HINT_PREFIX}2_") for k in hints)

    def test_multiple_chains_independent(self):
        chains = [("x1", 1), ("x2", 2)]
        hints = compute_chain_hints({"x1": True, "x2": False}, chains, chain_length=4)
        # chain 1: anchor=True → False, True, False, True
        assert hints[f"{ALWAYS_HINT_PREFIX}1_1"] is False
        assert hints[f"{ALWAYS_HINT_PREFIX}1_2"] is True
        # chain 2: anchor=False → True, False, True, False
        assert hints[f"{ALWAYS_HINT_PREFIX}2_1"] is True
        assert hints[f"{ALWAYS_HINT_PREFIX}2_2"] is False

    def test_empty_chains_returns_empty(self):
        hints = compute_chain_hints({"x1": True}, [], chain_length=10)
        assert hints == {}


# ---------------------------------------------------------------------------
# 3. Long chain — correctness and speed
# ---------------------------------------------------------------------------

class TestLongChain:

    def test_1000_link_chain_hint_count(self):
        chains = [("x1", 1)]
        hints = compute_chain_hints({"x1": True}, chains, chain_length=LONG_CHAIN_LENGTH)
        assert len(hints) == LONG_CHAIN_LENGTH

    def test_1000_link_chain_all_keys_present(self):
        chains = [("x1", 1)]
        hints = compute_chain_hints({"x1": False}, chains, chain_length=LONG_CHAIN_LENGTH)
        for i in range(1, LONG_CHAIN_LENGTH + 1):
            assert f"{ALWAYS_HINT_PREFIX}1_{i}" in hints

    def test_1000_link_chain_values_alternate_correctly(self):
        chains = [("x1", 1)]
        hints = compute_chain_hints({"x1": True}, chains, chain_length=LONG_CHAIN_LENGTH)
        for i in range(1, LONG_CHAIN_LENGTH + 1):
            expected = (i % 2 == 1)  # True anchor → first link False, so odd links False
            # anchor=True → link 1 = False (odd=False), link 2 = True (even=True)
            expected = not (i % 2 == 1)
            assert hints[f"{ALWAYS_HINT_PREFIX}1_{i}"] is expected

    def test_1000_link_chain_computed_fast(self):
        """Hint computation for a 1000-link chain should be near-instant."""
        chains = [("x1", 1)]
        t0 = time.monotonic()
        compute_chain_hints({"x1": True}, chains, chain_length=LONG_CHAIN_LENGTH)
        elapsed = time.monotonic() - t0
        assert elapsed < 0.05  # 50ms is very generous for a simple loop

    def test_augment_1000_link_chain_injected_correctly(self):
        rng = random.Random(99)
        augmented, chains = augment_smt2(SIMPLE_FORMULA, LONG_CHAIN_LENGTH, max_count=1, rng=rng)
        assert len(chains) == 1
        anchor, chain_idx = chains[0]
        # All 1000 variables declared
        declared = re.findall(rf'\(declare-fun {re.escape(ALWAYS_HINT_PREFIX)}{chain_idx}_(\d+)', augmented)
        assert len(declared) == LONG_CHAIN_LENGTH
        # Formula still valid: (check-sat) still present
        assert "(check-sat)" in augmented
