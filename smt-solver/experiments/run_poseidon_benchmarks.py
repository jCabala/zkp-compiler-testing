#!/usr/bin/env python3
"""Run all Poseidon .smt2 benchmarks with cvc5 (direct) and our tool (circom backend)."""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path

SMT_SOLVER_DIR = Path(__file__).resolve().parents[1]
CLI = SMT_SOLVER_DIR / "cli.py"

DEFAULT_BENCHMARK_DIR = (
    SMT_SOLVER_DIR / "benchmarks/SMT-benchmarks/finite-field/poseidon"
)
DEFAULT_TIMEOUT = 60  # seconds


def _parse_result(stdout: str) -> str:
    s = stdout.lower()
    if "unsat" in s:
        return "unsat"
    if "sat" in s:
        return "sat"
    return "unknown"


def run_cvc5(smt2_file: Path, timeout: int, cvc5_bin: str) -> tuple[str, float]:
    cmd = [cvc5_bin, "--lang", "smt2", str(smt2_file)]
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        elapsed = time.perf_counter() - start
        return _parse_result(proc.stdout.decode("utf-8", errors="replace")), round(elapsed, 4)
    except subprocess.TimeoutExpired:
        return "timeout", round(time.perf_counter() - start, 4)


def run_our_tool(smt2_file: Path, timeout: int, solver: str) -> tuple[str, float]:
    cmd = [
        sys.executable, str(CLI), "solve", str(smt2_file),
        "--zk-dsl", "circom",
        "--solver", solver,
        "--solving-timeout", str(timeout),
    ]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout + 30,  # outer safety margin on top of internal timeout
            cwd=SMT_SOLVER_DIR,
        )
        elapsed = time.perf_counter() - start
        return _parse_result(proc.stdout.decode("utf-8", errors="replace")), round(elapsed, 4)
    except subprocess.TimeoutExpired:
        return "timeout", round(time.perf_counter() - start, 4)


def _summary(label: str, rows: list[dict], result_key: str, time_key: str) -> None:
    counts: dict[str, int] = {"sat": 0, "unsat": 0, "unknown": 0, "timeout": 0}
    for r in rows:
        counts[r[result_key]] = counts.get(r[result_key], 0) + 1
    solved = [r[time_key] for r in rows if r[result_key] in ("sat", "unsat")]
    print(f"\n{label}:")
    print(f"  sat={counts.get('sat',0)}  unsat={counts.get('unsat',0)}  "
          f"unknown={counts.get('unknown',0)}  timeout={counts.get('timeout',0)}")
    if solved:
        print(f"  solve times:  min={min(solved):.4f}s  "
              f"max={max(solved):.4f}s  mean={sum(solved)/len(solved):.4f}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Poseidon benchmarks with cvc5 (direct) and our tool (circom backend)."
    )
    parser.add_argument(
        "benchmark_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_BENCHMARK_DIR,
        help=f"Folder of .smt2 files (default: {DEFAULT_BENCHMARK_DIR})",
    )
    parser.add_argument(
        "--timeout", "-t", type=int, default=DEFAULT_TIMEOUT,
        help=f"Per-benchmark timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--cvc5", default="cvc5", help="Path to cvc5 binary (default: cvc5)",
    )
    parser.add_argument(
        "--our-solver", default="cvc5", choices=["z3", "cvc5"],
        help="SMT solver used inside our tool (default: cvc5)",
    )
    parser.add_argument(
        "--out", "-o", type=Path, default=None,
        help="Write results to this CSV file (optional)",
    )
    args = parser.parse_args()

    files = sorted(args.benchmark_dir.glob("*.smt2"))
    if not files:
        print(f"No .smt2 files found in {args.benchmark_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Benchmarks : {len(files)}")
    print(f"Timeout    : {args.timeout}s")
    print(f"cvc5 binary: {args.cvc5}")
    print(f"Our tool   : {CLI}  (--zk-dsl circom --solver {args.our_solver})")
    print()

    col = {"#": 4, "file": 26, "cvc5_res": 11, "cvc5_t": 10, "our_res": 11, "our_t": 10}
    header = (f"{'#':<{col['#']}} {'file':<{col['file']}} "
              f"{'cvc5 result':<{col['cvc5_res']}} {'cvc5 t(s)':>{col['cvc5_t']}}  "
              f"{'our result':<{col['our_res']}} {'our t(s)':>{col['our_t']}}")
    print(header)
    print("-" * len(header))

    rows = []
    for i, f in enumerate(files, 1):
        cvc5_result, cvc5_time = run_cvc5(f, args.timeout, args.cvc5)
        our_result, our_time = run_our_tool(f, args.timeout, args.our_solver)

        row = {
            "file": f.name,
            "cvc5_result": cvc5_result,
            "cvc5_time_s": cvc5_time,
            "our_result": our_result,
            "our_time_s": our_time,
        }
        rows.append(row)

        print(f"{i:<{col['#']}} {f.name:<{col['file']}} "
              f"{cvc5_result:<{col['cvc5_res']}} {cvc5_time:>{col['cvc5_t']}.4f}  "
              f"{our_result:<{col['our_res']}} {our_time:>{col['our_t']}.4f}")

    print("-" * len(header))
    _summary("cvc5 (direct)", rows, "cvc5_result", "cvc5_time_s")
    _summary("our tool (circom)", rows, "our_result", "our_time_s")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["file", "cvc5_result", "cvc5_time_s", "our_result", "our_time_s"],
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nResults written to {args.out}")


if __name__ == "__main__":
    main()
