from __future__ import annotations

from src.r1cs.ir import R1CS, LinearCombination, Constraint


def _lc_to_str(lc: LinearCombination) -> str:
	if not lc.terms:
		return "0"
	parts = []
	for t in lc.terms:
		parts.append(f"{t.coeff}*v{t.variable.index}")
	return " + ".join(parts)


def _constraint_to_str(c: Constraint) -> str:
	return f"({_lc_to_str(c.A)}) * ({_lc_to_str(c.B)}) = ({_lc_to_str(c.C)})"


def dump_r1cs(r1cs: R1CS) -> str:
	lines = []
	lines.append(f"prime: {r1cs.prime}")
	lines.append(f"nVars: {r1cs.nVars}")
	lines.append(f"nConstraints: {r1cs.nConstraints}")
	lines.append(f"bool_wires: {sorted(r1cs.bool_wire_indices)}")
	lines.append(f"ternary_wires: {sorted(r1cs.ternary_wire_indices)}")
	lines.append("")
	for i, c in enumerate(r1cs.constraints):
		lines.append(f"{i}: {_constraint_to_str(c)}")
	return "\n".join(lines) + "\n"
