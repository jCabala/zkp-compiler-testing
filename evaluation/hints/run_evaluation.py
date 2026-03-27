#!/usr/bin/env python3
"""Evaluate the effect of --with-hints on solve time across solvers and pruning levels."""

import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CLI = REPO_ROOT / "smt-solver" / "cli.py"

K_LEVELS = [5, 10, 15, 20]
SOLVERS = ["z3", "cvc5", "picus"]
DSLS = ["circom", "gnark"]
TIMEOUT = 120  # seconds
GNARK_TIMEOUT = 60  # seconds (gnark compilation can hang)


def run_solve(smt_file: Path, solver: str, dsl: str, with_hints: bool) -> dict:
    """Run the CLI solve command and return timing + result."""
    cmd = [
        sys.executable, str(CLI), "solve",
        str(smt_file),
        "--solver", solver,
        "--zk-dsl", dsl,
    ]
    if with_hints:
        cmd.append("--with-hints")

    timeout = GNARK_TIMEOUT if dsl == "gnark" else TIMEOUT
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT / "smt-solver"),
        )
        elapsed = time.monotonic() - start
        if result.returncode != 0:
            print(f"\nERROR: command failed (exit {result.returncode})")
            print(f"  cmd: {' '.join(cmd)}")
            print(f"  stderr: {result.stderr.strip()}")
            sys.exit(1)
        output = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
        return {
            "time": elapsed,
            "result": output,
            "exit_code": result.returncode,
            "error": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "time": timeout,
            "result": "TIMEOUT",
            "exit_code": -1,
            "error": "",
        }


def collect_files(k: int) -> list[Path]:
    d = SCRIPT_DIR / f"k{k}"
    if not d.exists():
        return []
    return sorted(d.glob("*.smt2"))


def main():
    rows = []

    for k in K_LEVELS:
        files = collect_files(k)
        if not files:
            print(f"No files for k={k}, skipping")
            continue

        for smt_file in files:
            for dsl in DSLS:
                for solver in SOLVERS:
                    for hints in [False, True]:
                        label = f"k={k:>2} | {dsl:<6} | {solver:<5} | hints={'Y' if hints else 'N'} | {smt_file.name}"
                        print(f"Running: {label} ...", end=" ", flush=True)
                        info = run_solve(smt_file, solver, dsl, hints)
                        print(f"{info['time']:.2f}s  {info['result']}")
                        rows.append({
                            "k": k,
                            "file": smt_file.name,
                            "dsl": dsl,
                            "solver": solver,
                            "hints": hints,
                            **info,
                        })

    if not rows:
        print("No results collected.")
        return

    # Print results table
    print("\n" + "=" * 110)
    print(f"{'k':>3}  {'file':<40} {'dsl':<7} {'solver':<6} {'hints':>5}  {'time(s)':>8}  {'result':<10}")
    print("-" * 110)
    for r in rows:
        print(
            f"{r['k']:>3}  {r['file']:<40} {r['dsl']:<7} {r['solver']:<6} {'Y' if r['hints'] else 'N':>5}  "
            f"{r['time']:>8.2f}  {r['result']:<10}"
        )

    # Summary: average speedup per dsl per solver per k
    print("\n" + "=" * 80)
    print("SPEEDUP SUMMARY (avg time without hints / avg time with hints)")
    print("-" * 80)
    print(f"{'k':>3}  {'dsl':<7} {'solver':<6}  {'no hints(s)':>12}  {'hints(s)':>10}  {'speedup':>8}")
    print("-" * 80)

    for k in K_LEVELS:
        for dsl in DSLS:
            for solver in SOLVERS:
                no_hint = [r["time"] for r in rows if r["k"] == k and r["dsl"] == dsl and r["solver"] == solver and not r["hints"]]
                with_hint = [r["time"] for r in rows if r["k"] == k and r["dsl"] == dsl and r["solver"] == solver and r["hints"]]
                if not no_hint or not with_hint:
                    continue
                avg_no = sum(no_hint) / len(no_hint)
                avg_yes = sum(with_hint) / len(with_hint)
                speedup = avg_no / avg_yes if avg_yes > 0 else float("inf")
                print(f"{k:>3}  {dsl:<7} {solver:<6}  {avg_no:>12.2f}  {avg_yes:>10.2f}  {speedup:>7.2f}x")

    print()


if __name__ == "__main__":
    main()
