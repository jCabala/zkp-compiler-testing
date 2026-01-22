from src.r1cs.ir import SMTResult
from typing import Any

def _safe_int(x: Any) -> int:
    """
    Convert solver values to Python int.

    Supports:
    - Z3 numerals: .as_long()
    - cvc5 pythonic numerals (including finite-field values): .as_long()
    - cvc5 base API integer values: .getIntegerValue()
    """
    try:
        return int(x)
    except Exception:
        pass
    if hasattr(x, "as_long"):
        return int(x.as_long())
    raise TypeError(f"Cannot convert model value to int: {x!r}")


def solve_r1cs_z3(r1cs, bool_vars: bool = False, with_logs: bool = False) -> SMTResult:
    from z3 import Solver, Int, Bool, sat
    solver = Solver()

    if bool_vars:
        var_map = {
            var.index: Bool(f"v{var.index}")
            for var in r1cs.variables
            if not var.is_constant_one()
        }
    else:
        var_map = {
            var.index: Int(f"v{var.index}")
            for var in r1cs.variables
            if not var.is_constant_one()
        }
        for var in r1cs.variables:
            if not var.is_constant_one():
                solver.add(var_map[var.index] >= 0)
                solver.add(var_map[var.index] < r1cs.prime)

    var_map[0] = 1  # constant-one wire
    p = r1cs.prime

    for constraint in r1cs.constraints:
        A = sum(t.coeff * var_map[t.variable.index] for t in constraint.A.terms)
        B = sum(t.coeff * var_map[t.variable.index] for t in constraint.B.terms)
        C = sum(t.coeff * var_map[t.variable.index] for t in constraint.C.terms)
        solver.add((A * B) % p == (C % p))

    if with_logs:
        print("SMT Query (Z3):")
        print(solver.assertions())

    if solver.check() == sat:
        m = solver.model()
        solution = {d.name(): _safe_int(m[d]) for d in m.decls()}
        return SMTResult(True, solution)

    return SMTResult(False, {})
