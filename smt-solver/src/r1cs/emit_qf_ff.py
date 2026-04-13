from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.r1cs.ir import R1CS, LinearCombination, Term


def emit_qf_ff(
	r1cs: R1CS,
	*,
	source_path: Path | None = None,
	backend: str | None = None,
) -> str:
	"""
	Serialize an R1CS instance into SMT-LIB v2 using QF_FF.

	This intentionally mirrors the finite-field semantics used by the cvc5 backend.
	"""
	p = int(r1cs.prime)
	lines: list[str] = []

	lines.append("; Auto-generated finite-field SMT-LIB (QF_FF)")
	if source_path is not None:
		lines.append(f"; source={source_path}")
	if backend is not None:
		lines.append(f"; backend={backend}")
	lines.append(f"; prime={p}")
	lines.append(f"; nVars={r1cs.nVars} nConstraints={r1cs.nConstraints}")
	lines.append("(set-logic QF_FF)")
	lines.append("")
	lines.append(f"(define-sort F () (_ FiniteField {p}))")
	lines.append("")

	# Declare variables (skip constant-one wire at index 0)
	for var in r1cs.variables:
		if var.is_constant_one():
			continue
		lines.append(f"(declare-fun v{var.index} () F)")
	lines.append("")

	def ff_const(val: int) -> str:
		return f"(as ff{val % p} F)"

	def ff_add(terms: Iterable[str]) -> str:
		terms = list(terms)
		if not terms:
			return ff_const(0)
		if len(terms) == 1:
			return terms[0]
		return f"(ff.add {' '.join(terms)})"

	def ff_mul(a: str, b: str) -> str:
		return f"(ff.mul {a} {b})"

	def ff_neg(a: str) -> str:
		return f"(ff.neg {a})"

	def ff_sub(a: str, b: str) -> str:
		return ff_add([a, ff_neg(b)])

	def term_to_expr(term: Term) -> str | None:
		coeff = term.coeff % p
		if coeff == 0:
			return None
		if term.variable.index == 0:
			return ff_const(coeff)
		var_ref = f"v{term.variable.index}"
		if coeff == 1:
			return var_ref
		return ff_mul(ff_const(coeff), var_ref)

	def lc_to_expr(lc: LinearCombination) -> str:
		parts: list[str] = []
		for t in lc.terms:
			expr = term_to_expr(t)
			if expr is not None:
				parts.append(expr)
		return ff_add(parts)

	# Boolean wire constraints: v * (v - 1) = 0
	for idx in sorted(r1cs.bool_wire_indices):
		if idx == 0:
			continue
		v = f"v{idx}"
		v_minus_1 = ff_sub(v, ff_const(1))
		lines.append(f"(assert (= {ff_mul(v, v_minus_1)} {ff_const(0)}))")

	# Ternary wire constraints: v * (v - 1) * (v + 1) = 0
	for idx in sorted(r1cs.ternary_wire_indices):
		if idx == 0:
			continue
		v = f"v{idx}"
		v_minus_1 = ff_sub(v, ff_const(1))
		v_plus_1 = ff_add([v, ff_const(1)])
		lines.append(f"(assert (= {ff_mul(v, ff_mul(v_minus_1, v_plus_1))} {ff_const(0)}))")

	# R1CS constraints: <A,x> * <B,x> = <C,x>
	for constraint in r1cs.constraints:
		A = lc_to_expr(constraint.A)
		B = lc_to_expr(constraint.B)
		C = lc_to_expr(constraint.C)
		lines.append(f"(assert (= {ff_mul(A, B)} {C}))")

	lines.append("")
	lines.append("(check-sat)")
	lines.append("")

	return "\n".join(lines)
