from src.r1cs.ir import Constraint
from src.r1cs.emit_qf_ff import emit_qf_ff
from tests.r1cs.conftest import lc, const, make_r1cs, PRIME


def test_emit_qf_ff_basic_structure():
	# A simple constraint: v1 * 1 = 1
	r1cs = make_r1cs(
		constraints=[Constraint(A=lc((1, 1)), B=const(1), C=const(1))],
		nvars=2,
	)
	smt2 = emit_qf_ff(r1cs)
	assert "(set-logic QF_FF)" in smt2
	assert f"(define-sort F () (_ FiniteField {PRIME}))" in smt2
	assert "(declare-fun v1 () F)" in smt2
	assert "(check-sat)" in smt2


def test_emit_qf_ff_bool_and_ternary_constraints():
	r1cs = make_r1cs(
		constraints=[Constraint(A=const(1), B=const(1), C=const(1))],
		nvars=3,
		bool_wires={1},
	)
	r1cs.ternary_wire_indices.add(2)
	smt2 = emit_qf_ff(r1cs)
	assert "(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))" in smt2
	assert "(assert (= (ff.mul v2 (ff.mul (ff.add v2 (ff.neg (as ff1 F))) (ff.add v2 (as ff1 F)))) (as ff0 F)))" in smt2


def test_emit_qf_ff_coeff_normalization():
	r1cs = make_r1cs(
		constraints=[Constraint(A=lc((-1, 1)), B=const(1), C=const(0))],
		nvars=2,
	)
	smt2 = emit_qf_ff(r1cs)
	assert f"(as ff{PRIME - 1} F)" in smt2
