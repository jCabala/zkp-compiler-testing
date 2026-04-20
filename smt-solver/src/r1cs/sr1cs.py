from __future__ import annotations

from src.r1cs.ir import Constraint, LinearCombination, R1CS


def dump_sr1cs(
    r1cs: R1CS,
    *,
    input_wires: list[int] | tuple[int, ...] = (),
    output_wires: list[int] | tuple[int, ...] = (),
) -> str:
    """Serialize the internal R1CS into the gnark-style .sr1cs text format."""
    surviving = {variable.index for variable in r1cs.variables}

    lines: list[str] = [f"(prime-number {r1cs.prime})"]

    for wire_idx in input_wires:
        if wire_idx in surviving:
            lines.append(f"(in {wire_idx})")

    for wire_idx in output_wires:
        if wire_idx in surviving:
            lines.append(f"(out {wire_idx})")

    for constraint in r1cs.constraints:
        lines.append(
            f"(constraint {_lc_to_group(constraint.A)} {_lc_to_group(constraint.B)} {_lc_to_group(constraint.C)})"
        )

    return "\n".join(lines) + "\n"


def _lc_to_group(lc: LinearCombination) -> str:
    if not lc.terms:
        return "[]"
    terms = " ".join(f"({term.coeff} {term.variable.index})" for term in lc.terms)
    return f"[{terms}]"
