"""Unit tests for R1CS optimization passes."""

import pytest
from src.r1cs.optimization.optimize import optimize_r1cs
from src.r1cs.ir import Constraint
from tests.r1cs.conftest import make_r1cs, lc, const, PRIME

P = PRIME


# ---- Helpers ----

def _bool_constraint(wire: int) -> Constraint:
    """v * v = v  →  v*(v-1) = 0  →  v is boolean."""
    return Constraint(
        A=lc((1, wire)),
        B=lc((1, wire)),
        C=lc((1, wire)),
    )


def _assignment_constraint(src: int, dst: int) -> Constraint:
    """src - dst = 0  →  dst = src (as a linear constraint: 1*src = 1*dst)."""
    return Constraint(
        A=lc((1, src)),
        B=const(1),
        C=lc((1, dst)),
    )


def _negation_constraint(v1: int, v2: int) -> Constraint:
    """v1 + v2 = 1  →  if one is boolean, other is too."""
    # (v1 + v2) * 1 = 1
    return Constraint(
        A=lc((1, v1), (1, v2)),
        B=const(1),
        C=const(1),
    )


def _multiplication_constraint(vx: int, vy: int, vz: int) -> Constraint:
    """vx * vy = vz."""
    return Constraint(
        A=lc((1, vx)),
        B=lc((1, vy)),
        C=lc((1, vz)),
    )


def _ternary_constraint(v1: int, v2: int, v3: int) -> Constraint:
    """v1 = v2 + v3  →  1*v1 - 1*v2 - 1*v3 = 0."""
    return Constraint(
        A=lc((1, v1), (P - 1, v2), (P - 1, v3)),
        B=const(1),
        C=const(0),
    )


# ---- Tests: bool constraint detection ----

class TestBoolConstraint:
    def test_detects_bool_wire(self):
        # v1 * v1 = v1  →  v1 is boolean
        r1cs = make_r1cs([_bool_constraint(1)], nvars=2)
        result = optimize_r1cs(r1cs)
        assert 1 in result.bool_wire_indices

    def test_no_false_positives(self):
        # v1 * v2 = v3 — no boolean detection expected
        r1cs = make_r1cs([_multiplication_constraint(1, 2, 3)], nvars=4)
        result = optimize_r1cs(r1cs)
        assert result.bool_wire_indices == set()

    def test_multiple_bool_constraints(self):
        r1cs = make_r1cs([_bool_constraint(1), _bool_constraint(2)], nvars=3)
        result = optimize_r1cs(r1cs)
        assert 1 in result.bool_wire_indices
        assert 2 in result.bool_wire_indices


# ---- Tests: bool assignment propagation ----

class TestBoolAssignmentPropagation:
    def test_propagates_bool_via_assignment(self):
        # v1 is boolean, v1 = v2  →  v2 should be boolean
        r1cs = make_r1cs(
            [_bool_constraint(1), _assignment_constraint(1, 2)],
            nvars=3,
        )
        result = optimize_r1cs(r1cs)
        assert 1 in result.bool_wire_indices
        assert 2 in result.bool_wire_indices

    def test_no_propagation_without_seed(self):
        # Assignment with no boolean seed — nothing propagates
        r1cs = make_r1cs([_assignment_constraint(1, 2)], nvars=3)
        result = optimize_r1cs(r1cs)
        assert result.bool_wire_indices == set()


# ---- Tests: bool negation propagation ----

class TestBoolNegationPropagation:
    def test_propagates_via_negation(self):
        # v1 is boolean, v1 + v2 = 1  →  v2 is boolean
        r1cs = make_r1cs(
            [_bool_constraint(1), _negation_constraint(1, 2)],
            nvars=3,
        )
        result = optimize_r1cs(r1cs)
        assert 2 in result.bool_wire_indices

    def test_no_propagation_without_seed(self):
        r1cs = make_r1cs([_negation_constraint(1, 2)], nvars=3)
        result = optimize_r1cs(r1cs)
        assert result.bool_wire_indices == set()


# ---- Tests: bool multiplication propagation ----

class TestBoolMultiplicationPropagation:
    def test_product_of_bools_is_bool(self):
        # v1, v2 boolean, v1*v2 = v3  →  v3 is boolean
        r1cs = make_r1cs(
            [_bool_constraint(1), _bool_constraint(2), _multiplication_constraint(1, 2, 3)],
            nvars=4,
        )
        result = optimize_r1cs(r1cs)
        assert 3 in result.bool_wire_indices

    def test_no_propagation_if_one_not_bool(self):
        # Only v1 is boolean, v2 unknown  →  v3 not inferred
        r1cs = make_r1cs(
            [_bool_constraint(1), _multiplication_constraint(1, 2, 3)],
            nvars=4,
        )
        result = optimize_r1cs(r1cs)
        assert 3 not in result.bool_wire_indices


# ---- Tests: ternary detection ----

class TestTernaryDetection:
    def test_detects_ternary_wire(self):
        # v1, v2 boolean, v1 = v2 + v3  →  v3 is ternary
        r1cs = make_r1cs(
            [_bool_constraint(1), _bool_constraint(2), _ternary_constraint(1, 2, 3)],
            nvars=4,
        )
        result = optimize_r1cs(r1cs)
        assert 3 in result.ternary_wire_indices

    def test_no_ternary_without_two_bools(self):
        # Only one bool — not enough to infer ternary
        r1cs = make_r1cs(
            [_bool_constraint(1), _ternary_constraint(1, 2, 3)],
            nvars=4,
        )
        result = optimize_r1cs(r1cs)
        assert 3 not in result.ternary_wire_indices


# ---- Tests: fixpoint and no-op ----

class TestFixpoint:
    def test_empty_r1cs_unchanged(self):
        r1cs = make_r1cs([], nvars=3)
        result = optimize_r1cs(r1cs)
        assert result.bool_wire_indices == set()
        assert result.ternary_wire_indices == set()

    def test_pre_seeded_bools_preserved(self):
        r1cs = make_r1cs([], nvars=3, bool_wires={1, 2})
        result = optimize_r1cs(r1cs)
        assert 1 in result.bool_wire_indices
        assert 2 in result.bool_wire_indices

    def test_multi_hop_propagation(self):
        # v1 bool → v2 (assignment) → v3 (assignment): requires 2 iterations
        r1cs = make_r1cs(
            [_bool_constraint(1), _assignment_constraint(1, 2), _assignment_constraint(2, 3)],
            nvars=4,
        )
        result = optimize_r1cs(r1cs)
        assert 1 in result.bool_wire_indices
        assert 2 in result.bool_wire_indices
        assert 3 in result.bool_wire_indices
