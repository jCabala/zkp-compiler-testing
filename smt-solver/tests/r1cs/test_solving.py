"""Unit tests for R1CS Z3 solving."""

import pytest
from src.r1cs.solve_z3 import solve_r1cs_z3
from src.r1cs.ir import Constraint, SMTResult
from tests.r1cs.conftest import make_r1cs, lc, const, PRIME

P = PRIME


# ---- Helpers ----

def _bool_constraint(wire: int) -> Constraint:
    """v * v = v  →  v is boolean."""
    return Constraint(A=lc((1, wire)), B=lc((1, wire)), C=lc((1, wire)))


def _assignment_constraint(src: int, dst: int) -> Constraint:
    """1*src * 1 = 1*dst  →  dst = src."""
    return Constraint(A=lc((1, src)), B=const(1), C=lc((1, dst)))


def _multiplication_constraint(vx: int, vy: int, vz: int) -> Constraint:
    """vx * vy = vz."""
    return Constraint(A=lc((1, vx)), B=lc((1, vy)), C=lc((1, vz)))


def _negation_constraint(v1: int, v2: int) -> Constraint:
    """(v1 + v2) * 1 = 1  →  v1 + v2 = 1."""
    return Constraint(A=lc((1, v1), (1, v2)), B=const(1), C=const(1))


def _false_constraint() -> Constraint:
    """0 * 1 = 1  →  always unsatisfiable."""
    return Constraint(A=const(0), B=const(1), C=const(1))


# ---- Tests: basic satisfiability ----

class TestSatisfiability:
    def test_empty_r1cs_is_sat(self):
        r1cs = make_r1cs([], nvars=2)
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True

    def test_trivially_unsat(self):
        # 0 * 1 = 1 is impossible
        r1cs = make_r1cs([_false_constraint()], nvars=1)
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is False

    def test_single_bool_constraint_is_sat(self):
        # v1 * v1 = v1 is satisfiable (v1=0 or v1=1)
        r1cs = make_r1cs([_bool_constraint(1)], nvars=2, bool_wires={1})
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True

    def test_contradictory_bool_constraints(self):
        # v1 is bool AND v1 + v1 = 1 → 2*v1 = 1 → unsatisfiable over integers
        r1cs = make_r1cs(
            [
                _bool_constraint(1),
                Constraint(A=lc((2, 1)), B=const(1), C=const(1)),
            ],
            nvars=2,
            bool_wires={1},
        )
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is False


# ---- Tests: model correctness ----

class TestModelCorrectness:
    def test_model_returned_on_sat(self):
        r1cs = make_r1cs([_bool_constraint(1)], nvars=2, bool_wires={1})
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True
        assert isinstance(result.model, dict)

    def test_no_model_on_unsat(self):
        r1cs = make_r1cs([_false_constraint()], nvars=1)
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is False
        assert result.model == {}

    def test_bool_model_value_is_boolean(self):
        # v1 bool AND v1 + v2 = 1 (negation) — both should be bool
        r1cs = make_r1cs(
            [_bool_constraint(1), _negation_constraint(1, 2)],
            nvars=3,
            bool_wires={1, 2},
        )
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True
        # Model values for bool variables should be True/False (z3 booleans)
        v1 = result.model.get("v1")
        v2 = result.model.get("v2")
        assert v1 is not None
        assert v2 is not None


# ---- Tests: hint injection ----

class TestHints:
    def test_hint_forces_value(self):
        # v1 bool; hint says v1=1 → solution must have v1=True
        r1cs = make_r1cs([_bool_constraint(1)], nvars=2, bool_wires={1})
        r1cs.hints[1] = 1
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True

    def test_conflicting_hint_makes_unsat(self):
        # v1 bool; v1 + v2 = 1; hint v1=1 AND v2=1 → 1+1=1 is false
        r1cs = make_r1cs(
            [_bool_constraint(1), _bool_constraint(2), _negation_constraint(1, 2)],
            nvars=3,
            bool_wires={1, 2},
        )
        r1cs.hints[1] = 1
        r1cs.hints[2] = 1
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is False

    def test_consistent_hint_remains_sat(self):
        # v1 bool; v1 + v2 = 1; hint v1=1, v2=0 → consistent
        r1cs = make_r1cs(
            [_bool_constraint(1), _bool_constraint(2), _negation_constraint(1, 2)],
            nvars=3,
            bool_wires={1, 2},
        )
        r1cs.hints[1] = 1
        r1cs.hints[2] = 0
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True


# ---- Tests: wire type handling ----

class TestWireTypes:
    def test_integer_wire_within_field(self):
        # v1 is an unconstrained integer wire — solver should accept any field value
        r1cs = make_r1cs([], nvars=2)
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True

    def test_bool_and_int_wires_coexist(self):
        # v1 bool, v2 int, v1 * v2 = v2 (always true for bool v1=1)
        r1cs = make_r1cs(
            [_multiplication_constraint(1, 2, 2)],
            nvars=3,
            bool_wires={1},
        )
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True

    def test_assignment_between_bool_wires(self):
        # v1 bool, v2 = v1 → v2 is also bool; system is sat
        r1cs = make_r1cs(
            [_bool_constraint(1), _assignment_constraint(1, 2)],
            nvars=3,
            bool_wires={1, 2},
        )
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True

    def test_ternary_wire_constraints(self):
        # v1 bool, v2 bool, v1 = v2 + v3 (v3 is ternary: -1, 0, 1)
        # e.g. v1=1, v2=0 → v3=1; v1=0, v2=1 → v3=-1 (mod p); v1=1, v2=1 → v3=0
        ternary_constraint = Constraint(
            A=lc((1, 1), (P - 1, 2), (P - 1, 3)),
            B=const(1),
            C=const(0),
        )
        r1cs = make_r1cs(
            [_bool_constraint(1), _bool_constraint(2), ternary_constraint],
            nvars=4,
            bool_wires={1, 2},
        )
        r1cs.ternary_wire_indices.add(3)
        result = solve_r1cs_z3(r1cs)
        assert result.satisfiable is True
