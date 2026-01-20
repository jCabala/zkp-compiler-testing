from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Literal
from src.r1cs.solve_cvc5 import solve_r1cs_cvc5
from src.r1cs.solve_z3 import solve_r1cs_z3
from src.r1cs.ir import R1CS, SMTResult

BackendName = Literal["z3", "cvc5"]

# -----------------------
# Unified entry point
# -----------------------

def solve_r1cs(
    r1cs: R1CS,
    bool_vars: bool = False,
    backend: BackendName = "cvc5",
    with_logs: bool = True,
) -> SMTResult:
    if with_logs:
        print(f"Solving R1CS using {backend}...")
    if backend == "z3":
        return solve_r1cs_z3(r1cs, bool_vars=bool_vars, with_logs=with_logs)
    if backend == "cvc5":
        # Cvc should be run in a separate process to avoid issues with click and cvc5's internal state.
        return solve_r1cs_cvc5(r1cs, bool_vars=bool_vars, with_logs=with_logs)
    raise ValueError(f"Unknown backend: {backend!r}")
