#!/usr/bin/env python3
"""
Run NOT-chain profiling on finite-field SMT2 benchmark folders.

This is the finite-field companion to `test_not_chain_profiling.py`: it
iterates over FF benchmark directories, runs baseline vs augmented profiling
for each folder, and stores one JSON result file per folder.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SMT_SOLVER_DIR = REPO_ROOT / "smt-solver"
RUNNER = SCRIPT_DIR / "test_not_chain_profiling.py"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run NOT-chain profiling on FF benchmarks"
    )
    parser.add_argument(
        "--benchmarks-root",
        type=Path,
        default=SMT_SOLVER_DIR / "benchmarks" / "SMT-benchmarks" / "finite-field",
        help="Root directory containing FF benchmark folders",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="unique_sat_1to5vars_circom_O*",
        help="Glob pattern for benchmark folders under benchmarks-root",
    )
    parser.add_argument(
        "--file-pattern",
        type=str,
        default="*.smt2",
        help="Glob pattern for SMT2 files inside each benchmark folder",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=10,
        help="Max files per benchmark folder",
    )
    parser.add_argument(
        "--not-chain-length",
        type=int,
        default=400,
        help="Length of each injected linear chain",
    )
    parser.add_argument(
        "--max-not-chain-count",
        type=int,
        default=3,
        help="Max number of injected chains per benchmark",
    )
    parser.add_argument(
        "--solver",
        choices=["z3", "cvc5"],
        default="cvc5",
        help="Solver to use for the solve CLI pass",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Per-file timeout in seconds",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SCRIPT_DIR / "results-ff-not-chain",
        help="Directory to store per-folder JSON results",
    )
    parser.add_argument(
        "--compiler",
        type=Path,
        default=None,
        help="Optional profiling circom binary to forward to the underlying runner",
    )
    args = parser.parse_args()

    folders = sorted(args.benchmarks_root.glob(args.pattern))
    if not folders:
        print(
            f"No benchmark folders found under {args.benchmarks_root} matching {args.pattern}"
        )
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for folder in folders:
        out_file = args.output_dir / f"{folder.name}.json"
        print(f"\n=== NOT-chain profiling {folder} ===")
        cmd = [
            sys.executable,
            str(RUNNER),
            "--benchmarks-dir",
            str(folder),
            "--pattern",
            args.file_pattern,
            "--max-files",
            str(args.max_files),
            "--not-chain-length",
            str(args.not_chain_length),
            "--max-not-chain-count",
            str(args.max_not_chain_count),
            "--solver",
            args.solver,
            "--timeout",
            str(args.timeout),
            "--output",
            str(out_file),
        ]
        if args.compiler is not None:
            cmd.extend(["--compiler", str(args.compiler)])
        _run(cmd)

    print(f"\nDone. Results saved to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
