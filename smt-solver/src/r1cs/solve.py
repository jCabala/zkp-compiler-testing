from __future__ import annotations
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Dict, Literal
from src.r1cs.solve_z3 import solve_r1cs_z3
from src.r1cs.ir import R1CS, SMTResult

BackendName = Literal["z3", "cvc5"]

# ---------------------------------------------
# Unified entry point to the SMT solver solving
# ---------------------------------------------

# Inline script for the cvc5 subprocess: imports cvc5 before anything else,
# reads a pickled R1CS from stdin, solves, writes a pickled SMTResult to stdout.
_CVC5_WORKER = """\
import cvc5.pythonic  # must be first — before pysmt or any Cython extension
import pickle, sys
sys.path.insert(0, sys.argv[1])  # repo smt-solver dir
from src.r1cs.solve_cvc5 import solve_r1cs_cvc5
r1cs = pickle.loads(sys.stdin.buffer.read())
result = solve_r1cs_cvc5(r1cs)
sys.stdout.buffer.write(pickle.dumps(result))
"""

def _solve_cvc5_subprocess(r1cs: R1CS, with_logs: bool) -> SMTResult:
    """Run cvc5 in a fresh subprocess to avoid Cython/pysmt state conflicts."""
    smt_solver_dir = str(Path(__file__).resolve().parents[2])
    proc = subprocess.run(
        [sys.executable, "-c", _CVC5_WORKER, smt_solver_dir],
        input=pickle.dumps(r1cs),
        capture_output=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"cvc5 subprocess failed:\n{stderr}")
    if with_logs and proc.stderr:
        print(proc.stderr.decode("utf-8", errors="replace"), end="")
    return pickle.loads(proc.stdout)


def solve_r1cs(
    r1cs: R1CS,
    backend: BackendName = "cvc5",
    with_logs: bool = True,
) -> SMTResult:
    if with_logs:
        print(f"Solving R1CS using {backend}...")
    if backend == "z3":
        return solve_r1cs_z3(r1cs, with_logs=with_logs)
    if backend == "cvc5":
        return _solve_cvc5_subprocess(r1cs, with_logs=with_logs)
    raise ValueError(f"Unknown backend: {backend!r}")
