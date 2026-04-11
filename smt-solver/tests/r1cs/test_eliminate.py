"""Unit tests for removable-wire elimination."""

from src.r1cs.optimization.eliminate import eliminate_wires
from src.r1cs.ir import Constraint
from tests.r1cs.conftest import PRIME, make_r1cs, lc, const


def _assignment_constraint(src: int, dst: int) -> Constraint:
    """src - dst = 0  ->  dst = src."""
    return Constraint(
        A=lc((1, src)),
        B=const(1),
        C=lc((1, dst)),
    )


class TestEliminateWires:
    def test_noop_when_removable_set_empty(self):
        original = make_r1cs([_assignment_constraint(1, 2)], nvars=3, bool_wires={1, 2})

        result = eliminate_wires(original, set())

        assert result.nConstraints == 1
        assert result.constraints == original.constraints
        assert result.bool_wire_indices == {1, 2}

    def test_drops_constraint_when_all_wires_are_removable(self):
        r1cs = make_r1cs([_assignment_constraint(1, 2)], nvars=3)

        result = eliminate_wires(r1cs, {1, 2})

        assert result.nConstraints == 0
        assert result.constraints == []

    def test_drops_constraint_when_any_wire_is_removable(self):
        r1cs = make_r1cs(
            [
                _assignment_constraint(1, 2),
                _assignment_constraint(3, 4),
            ],
            nvars=5,
            bool_wires={2, 4},
        )

        result = eliminate_wires(r1cs, {2})

        assert result.nConstraints == 1
        assert result.constraints == [_assignment_constraint(3, 4)]
        assert result.bool_wire_indices == {4}

    def test_prunes_removable_variables_and_hints_from_r1cs(self):
        r1cs = make_r1cs([_assignment_constraint(3, 4)], nvars=5, bool_wires={2, 4})
        r1cs.ternary_wire_indices = {1, 3}
        r1cs.hints = {1: 10, 2: 20, 3: 30, 4: 40}

        result = eliminate_wires(r1cs, {1, 2})

        assert [v.index for v in result.variables] == [0, 3, 4]
        assert result.nVars == 3
        assert result.bool_wire_indices == {4}
        assert result.ternary_wire_indices == {3}
        assert result.hints == {3: 30, 4: 40}

    def test_removes_transitive_helper_cone_but_keeps_protected_wires(self):
        r1cs = make_r1cs(
            [
                # x1 + removable -> helper5
                Constraint(A=lc((1, 1), (1, 2), (PRIME - 1, 5)), B=const(1), C=const(0)),
                # helper5 -> helper6
                _assignment_constraint(5, 6),
                # independent real-variable constraint should survive
                _assignment_constraint(1, 3),
            ],
            nvars=7,
            bool_wires={1, 2},
        )

        result = eliminate_wires(r1cs, {2}, protected_indices={1})

        assert result.nConstraints == 1
        assert result.constraints == [_assignment_constraint(1, 3)]
        assert [v.index for v in result.variables] == [0, 1, 3, 4]
        assert result.bool_wire_indices == {1}

    def test_ignores_constant_wire_when_checking_removable(self):
        constant_only = Constraint(A=const(1), B=const(1), C=const(1))
        r1cs = make_r1cs([constant_only], nvars=1)

        result = eliminate_wires(r1cs, {99})

        assert result.nConstraints == 1
        assert result.constraints == [constant_only]
