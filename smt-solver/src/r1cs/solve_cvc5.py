from __future__ import annotations
from typing import Any, Dict
from src.r1cs.ir import SMTResult

def _safe_int(x: Any) -> int:
    # cvc5 pythonic finite-field numerals
    if hasattr(x, "as_long"):
        return int(x.as_long())

    # sometimes useful if you want signed representative
    if hasattr(x, "as_signed_long"):
        return int(x.as_signed_long())

    # base API sometimes exposes this (not usually in pythonic wrappers)
    if hasattr(x, "getIntegerValue"):
        return int(x.getIntegerValue())

    # last resort: Python ints etc.
    try:
        return int(x)
    except Exception:
        raise TypeError(f"Cannot convert model value to int: {x!r} (type={type(x)})")


def solve_r1cs_cvc5(r1cs, with_logs: bool = False) -> SMTResult:
    # impirts inside to avaoid cvc vc z3 conflicts
    import cvc5.pythonic as cv

    p = int(r1cs.prime)
    F = cv.FiniteFieldSort(p)

    # Prefer a field logic. If your build complains about the logic name,
    # you can fall back to `Solver()` without specifying one.
    solver = cv.SolverFor("QF_FF")
    # Helper: finite-field constant (reduces mod p automatically)
    def ff_val(n: int):
        return cv.FiniteFieldVal(int(n) % p, F)

    # Build variables in F_p
    var_map: Dict[int, Any] = {}

    for var in r1cs.variables:
        if var.is_constant_one():
            continue
        name = f"v{var.index}"
        v = cv.FiniteFieldElem(name, F)
        var_map[var.index] = v
        
        # If this wire should be boolean, add constraint: v * (v - 1) = 0
        if var.index in r1cs.bool_wire_indices:
            solver.add(v * (v - ff_val(1)) == ff_val(0))
        
        # If this wire should be ternary, add constraint: v * (v - 1) * (v + 1) = 0
        # This means v ∈ {p-1, 0, 1} in the finite field
        # Common pattern: when v1 = v2 + v3 where v1, v2 are boolean,
        # then v3 can only be -1, 0, or 1 (represented as p-1, 0, 1 in finite field)
        elif var.index in r1cs.ternary_wire_indices:
            solver.add(v * (v - ff_val(1)) * (v + ff_val(1)) == ff_val(0))

    # Constant-one wire in the field
    var_map[0] = ff_val(1)

    def lincomb(lc):
        # Σ (coeff_i * v_i) in F_p
        acc = ff_val(0)
        for t in lc.terms:
            acc = acc + (ff_val(t.coeff) * var_map[t.variable.index])
        return acc

    # Assert R1CS constraints: <A,x> * <B,x> == <C,x> in F_p
    for constraint in r1cs.constraints:
        A = lincomb(constraint.A)
        B = lincomb(constraint.B)
        C = lincomb(constraint.C)
        solver.add(A * B == C)

    if with_logs:
        print("p = ", p)
        print("SMT Query (cvc5 pythonic, finite field):")
        print(solver.assertions())

    res = solver.check()
    if res == cv.sat:
        m = solver.model()
        if with_logs:
            print("SMT Model (cvc5 pythonic):")
        solution: Dict[str, int] = {}

        # Extract values for declared vars (skip constant wire)
        for idx, v in var_map.items():
            if idx == 0:
                continue
            # model().eval(...) returns a finite-field value; as_long() gives a canonical rep in [0, p-1]
            val = m.eval(v)
            solution[f"v{idx}"] = _safe_int(val)

        return SMTResult(True, solution)

    return SMTResult(False, {})
