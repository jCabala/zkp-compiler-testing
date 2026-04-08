from __future__ import annotations
from typing import Literal
from src.r1cs.solve_z3 import solve_r1cs_z3
from src.r1cs.solve_cvc5 import solve_cvc5_subprocess
from src.r1cs.ir import R1CS, SMTResult

BackendName = Literal["z3", "cvc5"]


def solve_r1cs(
    r1cs: R1CS,
    backend: BackendName = "cvc5",
    with_logs: bool = True,
    solving_timeout: int | None = None,
) -> SMTResult:
    if with_logs:
        print(f"Solving R1CS using {backend}...")
    if backend == "z3":
        return solve_r1cs_z3(r1cs, with_logs=with_logs, solving_timeout=solving_timeout)
    if backend == "cvc5":
        return solve_cvc5_subprocess(r1cs, with_logs=with_logs, solving_timeout=solving_timeout)
    raise ValueError(f"Unknown backend: {backend!r}")
