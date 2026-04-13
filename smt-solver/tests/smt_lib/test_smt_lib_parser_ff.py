from src.smt_lib.smt_lib_parser import parse_smtlib2
from src.smt_lib.zk_ir import VariableType, BinaryExpression, UnaryExpression, Operator, Integer, Variable


def test_parse_qf_ff_basic():
	smt2 = """\
(set-logic QF_FF)
(define-sort F () (_ FiniteField 101))
(declare-fun x () F)
(declare-fun y () F)
(assert (= (ff.add x (ff.neg y)) (as ff2 F)))
(check-sat)
"""
	circuit = parse_smtlib2(smt2)
	assert [v.name for v in circuit.inputs] == ["x", "y"]
	assert all(v.variable_type == VariableType.FIELD for v in circuit.inputs)
	assert len(circuit.statements) == 1

	stmt = circuit.statements[0]
	assert isinstance(stmt.value, BinaryExpression)
	assert stmt.value.op == Operator.EQU
	lhs = stmt.value.lhs
	rhs = stmt.value.rhs
	assert isinstance(lhs, BinaryExpression)
	assert lhs.op == Operator.ADD
	assert isinstance(lhs.lhs, Variable) and lhs.lhs.name == "x"
	assert isinstance(lhs.rhs, UnaryExpression)
	assert lhs.rhs.op == Operator.SUB
	assert isinstance(lhs.rhs.value, Variable) and lhs.rhs.value.name == "y"
	assert isinstance(rhs, Integer) and rhs.value == 2


def test_parse_qf_ff_mul():
	smt2 = """\
(set-logic QF_FF)
(define-sort F () (_ FiniteField 101))
(declare-fun x () F)
(declare-fun y () F)
(declare-fun z () F)
(assert (= (ff.mul x y z) (as ff5 F)))
(check-sat)
"""
	circuit = parse_smtlib2(smt2)
	stmt = circuit.statements[0]
	assert isinstance(stmt.value, BinaryExpression)
	assert stmt.value.op == Operator.EQU
	lhs = stmt.value.lhs
	assert isinstance(lhs, BinaryExpression)
	assert lhs.op == Operator.MUL


def test_parse_qf_ff_sum_fusion():
	smt2 = """\
(set-logic QF_FF)
(define-sort F () (_ FiniteField 101))
(declare-fun x1 () F)
(declare-fun x2 () F)
(declare-fun x1__x2__orig__x1__x2__fused () F)
(assert (= (ff.add x1 x2) (as ff0 F)))
(check-sat)
"""
	circuit = parse_smtlib2(smt2)
	fused = [v for v in circuit.outputs if v.name.endswith("_fused")]
	assert len(fused) == 1
	assert isinstance(fused[0].fusion_expression, BinaryExpression)
	assert fused[0].fusion_expression.op == Operator.ADD
