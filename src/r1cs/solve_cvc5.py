from cvc5.pythonic import SolverFor, FiniteFieldSort, FiniteFieldElems, sat
from src.r1cs.ir import SMTResult
from typing import Any

# -----------------------
# cvc5 backend (FINITE FIELD THEORY)
# -----------------------

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
    if hasattr(x, "getIntegerValue"):  # cvc5 base API (integers)
        return int(x.getIntegerValue())
    raise TypeError(f"Cannot convert model value to int: {x!r}")


def solve_r1cs_cvc5(r1cs, bool_vars: bool = False, with_logs: bool = False) -> SMTResult:
    """
    Solve R1CS over the *true finite field* F_p using cvc5's Pythonic finite-field theory.

    Key differences vs the previous Int+mod encoding:
    - Variables live in FiniteField(p), not Int
    - Constraints are asserted as A*B == C directly in the field
    - No explicit bounds, no INTS_MODULUS
    """
    print("AAAAAAAAAAAAAa")
    p = 17
    F = FiniteFieldSort(p)
    x, y = FiniteFieldElems("x y", F)

    s = SolverFor("QF_FF")
    print("AAAAAAAAAAAAAa")
    s.add(x * y == 1)
    print("AAAAAAAAAAAAAa")
    s.add(x == 2)
    print("AAAAAAAAAAAAAa")
    s.add(x == 2)
    print("AAAAAAAAAAAAAa")
    r = s.check()
    print("result:", r)
    print("model y:", s.model()[y])
    return SMTResult(False, {})

    # p = int(r1cs.prime)
    # F = FiniteFieldSort(p)

    # # Prefer a field logic. If your build complains about the logic name,
    # # you can fall back to `Solver()` without specifying one.
    # solver = SolverFor("QF_FF")

    # # Helper: finite-field constant (reduces mod p automatically)
    # def ff_val(n: int):
    #     return FiniteFieldVal(int(n) % p, F)

    # # Build variables in F_p
    # var_map: Dict[int, Any] = {}

    # for var in r1cs.variables:
    #     if var.is_constant_one():
    #         continue
    #     name = f"v{var.index}"
    #     v = FiniteFieldElem(name, F)
    #     var_map[var.index] = v

    #     # If requested, restrict variables to {0,1} ⊆ F_p:
    #     # v is boolean iff v*(v-1) = 0 in a field
    #     if bool_vars:
    #         solver.add(v * (v - ff_val(1)) == ff_val(0))

    # # Constant-one wire in the field
    # var_map[0] = ff_val(1)

    # def lincomb(lc):
    #     # Σ (coeff_i * v_i) in F_p
    #     acc = ff_val(0)
    #     for t in lc.terms:
    #         acc = acc + (ff_val(t.coeff) * var_map[t.variable.index])
    #     return acc

    # # Assert R1CS constraints: <A,x> * <B,x> == <C,x> in F_p
    # for constraint in r1cs.constraints:
    #     A = lincomb(constraint.A)
    #     B = lincomb(constraint.B)
    #     C = lincomb(constraint.C)
    #     solver.add(A * B == C)

    # if with_logs:
    #     print("SMT Query (cvc5 pythonic, finite field):")
    #     print(solver.assertions())

    # res = solver.check()
    # if res == sat:
    #     m = solver.model()
    #     solution: Dict[str, int] = {}

    #     # Extract values for declared vars (skip constant wire)
    #     for idx, v in var_map.items():
    #         if idx == 0:
    #             continue
    #         # model().eval(...) returns a finite-field value; as_long() gives a canonical rep in [0, p-1]
    #         val = m.eval(v)
    #         solution[f"v{idx}"] = _safe_int(val)

    #     return SMTResult(True, solution)

    # return SMTResult(False, {})
