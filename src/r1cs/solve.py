from dataclasses import dataclass
from .ir import R1CS
from typing import Dict
from z3 import Solver, Int, sat

@dataclass
class SMTResult:
    satisfiable: bool
    model: Dict[str, int]  # variable assignments if satisfiable

def solve_r1cs(r1cs: R1CS) -> SMTResult:
    """
    Use z3 SMT solver to solve the given R1CS instance.
    """
    solver = Solver()
    var_map = {var.index: Int(f'v{var.index}') for var in r1cs.variables if not var.is_constant_one()}
    var_map[0] = 1  # constant one wire

    # Add constraints to the solver
    for constraint in r1cs.constraints:
        A_expr = sum(term.coeff * var_map[term.variable.index] for term in constraint.A.terms)
        B_expr = sum(term.coeff * var_map[term.variable.index] for term in constraint.B.terms)
        C_expr = sum(term.coeff * var_map[term.variable.index] for term in constraint.C.terms)
        solver.add((A_expr * B_expr) % r1cs.prime == C_expr % r1cs.prime)

    if solver.check() == sat:
        model = solver.model()
        solution = {d.name(): model[d].as_long() for d in model.decls()}
        return SMTResult(satisfiable=True, model=solution)
    else:
        return SMTResult(satisfiable=False, model={})

