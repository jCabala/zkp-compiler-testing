from src.r1cs.ir import SMTResult
from typing import Any

def solve_r1cs_z3(r1cs, with_logs: bool = False) -> SMTResult:
    from z3 import Solver, Int, Bool, Or, sat
    solver = Solver()

    # Create variables - Bool for boolean wires, Int for others
    var_map = {}
    p = r1cs.prime
    
    for var in r1cs.variables:
        if var.is_constant_one():
            continue
        
        if var.index in r1cs.bool_wire_indices:
            # Boolean variable (0 or 1)
            var_map[var.index] = Bool(f"v{var.index}")
        elif var.index in r1cs.ternary_wire_indices:
            # Ternary variable (p-1, 0, or 1)
            # Common pattern: when v1 = v2 + v3 where v1, v2 are boolean,
            # then v3 can only be -1, 0, or 1 (represented as p-1, 0, 1 in finite field)
            var_map[var.index] = Int(f"v{var.index}")
            solver.add(Or(var_map[var.index] == 0, 
                         var_map[var.index] == 1, 
                         var_map[var.index] == p - 1))
        else:
            # Integer variable with full field constraints
            var_map[var.index] = Int(f"v{var.index}")
            solver.add(var_map[var.index] >= 0)
            solver.add(var_map[var.index] < p)

    var_map[0] = 1  # constant-one wire

    for constraint in r1cs.constraints:
        A = sum(t.coeff * var_map[t.variable.index] for t in constraint.A.terms)
        B = sum(t.coeff * var_map[t.variable.index] for t in constraint.B.terms)
        C = sum(t.coeff * var_map[t.variable.index] for t in constraint.C.terms)
        solver.add((A * B) % p == (C % p))

    if with_logs:
        print("SMT Query (Z3):")
        print(solver.assertions())

    ret = solver.check()
    if ret == sat:
        m = solver.model()
        solution = {d.name(): m[d] for d in m.decls()}
        return SMTResult(True, solution)

    return SMTResult(False, {})
