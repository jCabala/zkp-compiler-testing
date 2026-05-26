#!/usr/bin/env python3
"""
Benchmark-size throughput experiment.

For each vars-NN benchmark directory, solve every benchmark and record
the wall-clock time. Results saved to obj/run-{timestamp}-{tag}/results.json.

Usage:
  python3 run.py [--hints|--no-hints] [--dsl circom|gnark|noir|zokrates]
                 [--solver cvc5|z3|picus] [--timeout SECS]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SMT_ROOT = (SCRIPT_DIR / "../../smt-solver").resolve()
BENCHMARKS_DIR = SCRIPT_DIR / "benchmarks"
ARTBUGS_CIRCOM = SMT_ROOT / "third_party/artificial-bugs/circom/target/release/circom"


def solve_one(
    smt_file: Path,
    dsl: str,
    solver: str,
    hints: bool,
    timeout: int,
) -> dict:
    cmd = [
        sys.executable,
        str(SMT_ROOT / "cli.py"),
        "solve",
        "--zk-dsl", dsl,
        "--solver", solver,
        "--solving-timeout", str(timeout),
    ]
    if dsl == "circom":
        cmd += ["--compiler", str(ARTBUGS_CIRCOM)]
    if not hints:
        cmd.append("--without-hints")
    cmd.append(str(smt_file))

    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        elapsed = time.perf_counter() - start
        out = proc.stdout.strip().lower()
        result = out if out in {"sat", "unsat", "unknown"} else "error"
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        result = "timeout"

    return {"elapsed_sec": round(elapsed, 4), "result": result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark-size throughput experiment")
    parser.add_argument(
        "--hints", action=argparse.BooleanOptionalAction, default=True,
        help="Enable adaptive hints (default: on)",
    )
    parser.add_argument("--dsl", default="circom", choices=["circom", "gnark", "noir", "zokrates"])
    parser.add_argument("--solver", default="cvc5", choices=["cvc5", "z3", "picus"])
    parser.add_argument("--timeout", type=int, default=60, help="Per-benchmark solve timeout (s)")
    parser.add_argument("--benchmarks-dir", type=Path, default=BENCHMARKS_DIR, help="Directory containing vars-NN subdirs")
    parser.add_argument("--max-per-var", type=int, default=5, help="Max benchmarks to run per vars-NN dir (default: 5)")
    args = parser.parse_args()

    ts = int(time.time())
    tag = f"hints={'on' if args.hints else 'off'}-dsl={args.dsl}-solver={args.solver}"
    out_dir = SCRIPT_DIR / "obj" / f"run-{ts}-{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "hints": args.hints,
        "dsl": args.dsl,
        "solver": args.solver,
        "timeout": args.timeout,
        "benchmarks_dir": str(args.benchmarks_dir),
    }

    results: list[dict] = []
    out_file = out_dir / "results.json"

    def flush() -> None:
        out_file.write_text(json.dumps({"metadata": metadata, "results": results}, indent=2))

    var_dirs = sorted(args.benchmarks_dir.glob("vars-??"))
    for var_dir in var_dirs:
        var_count = int(var_dir.name.split("-")[1])
        benchmarks = sorted(var_dir.glob("*.smt2"))[:args.max_per_var]
        if not benchmarks:
            print(f"vars={var_count:2d}  (empty, skipping)")
            continue
        print(f"vars={var_count:2d}  ({len(benchmarks)} benchmarks)")
        dir_results = []
        for bm in benchmarks:
            r = solve_one(bm, args.dsl, args.solver, args.hints, args.timeout)
            r.update({"vars": var_count, "benchmark": bm.name})
            dir_results.append(r)
            results.append(r)
            flush()
            print(f"  {bm.name:50s}  {r['result']:8s}  {r['elapsed_sec']:.3f}s")
        if all(r["result"] in {"timeout", "unknown"} for r in dir_results):
            print(f"\nAll {len(dir_results)} benchmarks timed out at vars={var_count}. Stopping.")
            break

    print(f"\nResults: {out_file}")


if __name__ == "__main__":
    main()
