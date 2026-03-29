"""Unit tests for the SMT-LIB v2 boolean parser."""

import pytest
import pysmt.environment


@pytest.fixture(autouse=True)
def reset_pysmt_env():
    """Reset pysmt's global environment to avoid symbol type conflicts between tests."""
    pysmt.environment.reset_env()
    yield
    pysmt.environment.reset_env()


from src.smt_lib.smt_lib_parser import parse_smtlib2_core, _infer_xor_fusion
from src.smt_lib.zk_ir import (
    Variable, Boolean, FusedVariable, UnaryExpression, BinaryExpression,
    Operator, VariableType, Assertion,
)


# ---- Helpers ----

def _parse(smt2: str):
    """Parse a boolean SMT-LIB formula and return the Circuit IR."""
    return parse_smtlib2_core(smt2)


def _single_assert_expr(smt2: str):
    """Parse a formula with a single assertion and return its expression."""
    circuit = _parse(smt2)
    assert len(circuit.statements) == 1
    return circuit.statements[0].value


def _formula(body: str, vars: list[str] = None) -> str:
    """Build a minimal SMT-LIB formula string."""
    if vars is None:
        vars = ["x", "y", "z"]
    decls = "\n".join(f"(declare-fun {v} () Bool)" for v in vars)
    return f"(set-logic QF_BV)\n{decls}\n{body}\n(check-sat)"


# ---- Tests: Variable extraction ----

class TestVariableExtraction:
    def test_single_variable(self):
        circuit = _parse(_formula("(assert x)", vars=["x"]))
        assert len(circuit.inputs) == 1
        assert circuit.inputs[0].name == "x"
        assert circuit.inputs[0].variable_type == VariableType.BOOLEAN

    def test_multiple_variables(self):
        circuit = _parse(_formula("(assert (and x y z))"))
        names = {v.name for v in circuit.inputs}
        assert names == {"x", "y", "z"}

    def test_all_variables_are_boolean(self):
        circuit = _parse(_formula("(assert x)", vars=["x"]))
        for v in circuit.inputs:
            assert v.variable_type == VariableType.BOOLEAN

    def test_no_variables(self):
        smt2 = "(set-logic QF_BV)\n(assert true)\n(check-sat)"
        circuit = _parse(smt2)
        assert len(circuit.inputs) == 0


# ---- Tests: Boolean constants ----

class TestBooleanConstants:
    def test_true(self):
        expr = _single_assert_expr(_formula("(assert true)", vars=[]))
        assert isinstance(expr, Boolean)
        assert expr.value is True

    def test_false(self):
        expr = _single_assert_expr(_formula("(assert false)", vars=[]))
        assert isinstance(expr, Boolean)
        assert expr.value is False


# ---- Tests: Boolean operations ----

class TestBooleanOperations:
    def test_not(self):
        expr = _single_assert_expr(_formula("(assert (not x))", vars=["x"]))
        assert isinstance(expr, UnaryExpression)
        assert expr.op == Operator.NOT
        assert isinstance(expr.value, Variable)
        assert expr.value.name == "x"

    def test_and_binary(self):
        expr = _single_assert_expr(_formula("(assert (and x y))", vars=["x", "y"]))
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LAND

    def test_and_nary(self):
        expr = _single_assert_expr(_formula("(assert (and x y z))"))
        # n-ary AND is folded left: (x AND y) AND z
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LAND
        assert isinstance(expr.lhs, BinaryExpression)
        assert expr.lhs.op == Operator.LAND

    def test_or_binary(self):
        expr = _single_assert_expr(_formula("(assert (or x y))", vars=["x", "y"]))
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LOR

    def test_or_nary(self):
        expr = _single_assert_expr(_formula("(assert (or x y z))"))
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LOR
        assert isinstance(expr.lhs, BinaryExpression)
        assert expr.lhs.op == Operator.LOR

    def test_implies(self):
        expr = _single_assert_expr(_formula("(assert (=> x y))", vars=["x", "y"]))
        # (=> x y) is rewritten as (or (not x) y)
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LOR
        assert isinstance(expr.lhs, UnaryExpression)
        assert expr.lhs.op == Operator.NOT

    def test_iff(self):
        expr = _single_assert_expr(_formula("(assert (= x y))", vars=["x", "y"]))
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.EQU

    def test_nested(self):
        expr = _single_assert_expr(_formula("(assert (and (or x y) (not z)))"))
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LAND
        assert isinstance(expr.lhs, BinaryExpression)
        assert expr.lhs.op == Operator.LOR
        assert isinstance(expr.rhs, UnaryExpression)
        assert expr.rhs.op == Operator.NOT


# ---- Tests: Multiple assertions ----

class TestMultipleAssertions:
    def test_multiple_asserts(self):
        smt2 = _formula("(assert x)\n(assert (not y))", vars=["x", "y"])
        circuit = _parse(smt2)
        assert len(circuit.statements) == 2
        assert all(isinstance(s, Assertion) for s in circuit.statements)
        assert circuit.statements[0].identifier == "assert_0"
        assert circuit.statements[1].identifier == "assert_1"


# ---- Tests: Circuit metadata ----

class TestCircuitMetadata:
    def test_circuit_name(self):
        circuit = _parse(_formula("(assert x)", vars=["x"]))
        assert circuit.name == "smtlib2_bool"

    def test_no_outputs_without_fused(self):
        circuit = _parse(_formula("(assert x)", vars=["x"]))
        assert len(circuit.outputs) == 0


# ---- Tests: XOR fusion inference ----

class TestXorFusion:
    def test_original_format(self):
        expr = _infer_xor_fusion("scr1_x1_scr1_x2_fused")
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LXOR
        assert isinstance(expr.lhs, Variable)
        assert expr.lhs.name == "scr1_x1"
        assert isinstance(expr.rhs, Variable)
        assert expr.rhs.name == "scr1_x2"

    def test_renamed_format(self):
        expr = _infer_xor_fusion("a__b__orig__something_fused")
        assert isinstance(expr, BinaryExpression)
        assert expr.op == Operator.LXOR
        assert isinstance(expr.lhs, Variable)
        assert expr.lhs.name == "a"
        assert isinstance(expr.rhs, Variable)
        assert expr.rhs.name == "b"

    def test_true_component(self):
        expr = _infer_xor_fusion("true__b__orig__something_fused")
        assert isinstance(expr.lhs, Boolean)
        assert expr.lhs.value is True

    def test_false_component(self):
        expr = _infer_xor_fusion("a__false__orig__something_fused")
        assert isinstance(expr.rhs, Boolean)
        assert expr.rhs.value is False

    def test_fused_variable_in_circuit(self):
        smt2 = _formula(
            "(assert (= scr1_x1_scr1_x2_fused (xor scr1_x1 scr1_x2)))",
            vars=["scr1_x1", "scr1_x2", "scr1_x1_scr1_x2_fused"],
        )
        circuit = _parse(smt2)
        fused = [v for v in circuit.outputs if isinstance(v, FusedVariable)]
        assert len(fused) == 1
        assert fused[0].name == "scr1_x1_scr1_x2_fused"
        assert fused[0].fusion_expression.op == Operator.LXOR

    def test_invalid_no_suffix(self):
        with pytest.raises(ValueError):
            _infer_xor_fusion("not_a_fused_var")

    def test_invalid_no_scr(self):
        with pytest.raises(ValueError):
            _infer_xor_fusion("abc_def_fused")


# ---- Tests: Error handling ----

class TestErrorHandling:
    def test_define_fun_raises(self):
        # define-fun without a body that pysmt would choke on:
        # use a formula where pysmt parses the define-fun but our code rejects it
        smt2 = "(set-logic QF_BV)\n(declare-fun x () Bool)\n(define-fun y () Bool x)\n(assert y)\n(check-sat)"
        with pytest.raises((NotImplementedError, Exception)):
            _parse(smt2)
