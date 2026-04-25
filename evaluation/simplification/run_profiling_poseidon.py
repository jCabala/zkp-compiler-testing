#!/usr/bin/env python3
"""
Run profiling-instrumented Circom on the Poseidon finite-field SMT2 benchmarks.

This is a thin wrapper around `run_profiling.py` with defaults tuned to the
Poseidon benchmark folder.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SMT_SOLVER_DIR = REPO_ROOT / "smt-solver"
RUN_PROFILING = SCRIPT_DIR / "run_profiling.py"
DEFAULT_BENCHMARKS = (
    SMT_SOLVER_DIR / "benchmarks" / "SMT-benchmarks" / "finite-field" / "poseidon"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile Circom on Poseidon benchmarks")
    parser.add_argument(
        "--benchmarks-dir",
        type=Path,
        default=DEFAULT_BENCHMARKS,
        help="Directory containing Poseidon .smt2 benchmarks",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=10,
        help="Maximum number of benchmark files to process",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout per compilation in seconds",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "results-poseidon.json",
        help="Path to save detailed JSON results",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(RUN_PROFILING),
        "--benchmarks-dir",
        str(args.benchmarks_dir),
        "--max-files",
        str(args.max_files),
        "--timeout",
        str(args.timeout),
        "--output",
        str(args.output),
    ]
    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
