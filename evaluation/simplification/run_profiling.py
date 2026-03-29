#!/usr/bin/env python3
"""
Run the profiling-instrumented Circom compiler on .smt2 benchmarks and collect
simplification statistics.

Usage:
    python run_profiling.py [--benchmarks-dir DIR] [--max-files N] [--timeout SECS] [--output results.json]

The script:
  1. Converts .smt2 files to .circom using the smt-solver's smt-to-dsl command
  2. Compiles each .circom directly with the profiling circom compiler (--r1cs --O2)
  3. Captures profiling JSON lines from stderr
  4. Aggregates and prints a summary

We compile circom directly (rather than using the `solve` command end-to-end)
because circom's stderr profiling output is captured and discarded by the
smt-solver's internal subprocess handling and never reaches our process.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SMT_SOLVER_DIR = REPO_ROOT / "smt-solver"
PROFILING_CIRCOM = REPO_ROOT / "evaluation" / "simplification" / "third_party" / "circom-profiling" / "target" / "release" / "circom"
DEFAULT_BENCHMARKS = SMT_SOLVER_DIR / "benchmarks" / "SMT-benchmarks" / "core" / "sat"
CIRCOMLIB_DIR = SMT_SOLVER_DIR / "experiments" / "circomlib"


def convert_smt_to_circom(smt2_files: list[Path], out_dir: Path, env: dict) -> list[Path]:
    """Convert .smt2 files to .circom using smt-to-dsl."""
    with tempfile.TemporaryDirectory() as tmp_in:
        tmp_in_path = Path(tmp_in)
        for f in smt2_files:
            shutil.copy(f, tmp_in_path / f.name)

        cmd = [
            sys.executable, "cli.py", "smt-to-dsl",
            str(tmp_in_path),
            str(out_dir),
            "--dsl", "circom",
        ]

        result = subprocess.run(
            cmd,
            cwd=str(SMT_SOLVER_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print(f"  smt-to-dsl error: {result.stderr[:500]}")
        if result.stdout:
            print(f"  {result.stdout.strip()}")

    return sorted(out_dir.glob("*.circom"))


def compile_circom(circom_path: Path, circomlib_path: Path, output_dir: Path, timeout: int) -> dict:
    """Compile a .circom file with profiling circom and capture profiling output."""
    cmd = [
        str(PROFILING_CIRCOM),
        str(circom_path),
        "--r1cs", "--O2",
        "-l", str(circomlib_path),
        "-o", str(output_dir),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        return {"file": circom_path.stem, "status": "timeout", "events": parse_profiling_events(stderr)}

    events = parse_profiling_events(result.stderr)
    status = "ok" if result.returncode == 0 else f"error (exit {result.returncode})"
    return {"file": circom_path.stem, "status": status, "events": events}


def parse_profiling_events(stderr: str) -> list[dict]:
    """Parse profiling JSON lines from stderr."""
    events = []
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def extract_summary(entry: dict) -> dict:
    """Extract key profiling metrics from a single benchmark's events."""
    summary = {
        "file": entry["file"],
        "status": entry["status"],
    }

    for ev in entry["events"]:
        event_type = ev.get("event", "")

        if event_type == "profiling_start":
            summary["initial_equalities"] = ev.get("initial_equalities", 0)
            summary["initial_cons_equalities"] = ev.get("initial_cons_equalities", 0)
            summary["initial_linear"] = ev.get("initial_linear", 0)
            summary["max_signal"] = ev.get("max_signal", 0)

        elif event_type == "eq_simplification":
            summary["eq_subs"] = ev.get("substitutions_produced", 0)

        elif event_type == "constant_eq_simplification":
            summary["ceq_subs"] = ev.get("substitutions_produced", 0)

        elif event_type == "linear_simplification" and not ev.get("skipped"):
            summary["lin_input"] = ev.get("input_constraints", 0)
            summary["lin_subs"] = ev.get("substitutions_produced", 0)

        elif event_type == "non_linear_simplification":
            summary["linearized_from_nonlinear"] = ev.get("linearized_from_nonlinear", 0)
            summary["storage_quadratic"] = ev.get("storage_quadratic", 0)

        elif event_type == "optimization_round":
            summary["total_rounds"] = max(
                summary.get("total_rounds", 0), ev.get("round", 0)
            )

        elif event_type == "operator_counts":
            for op in ["add", "sub", "mul", "div", "idiv", "mod", "pow",
                       "shift_l", "shift_r", "bit_or", "bit_and", "bit_xor"]:
                summary[f"op_{op}"] = ev.get(op, 0)
            summary["op_non_quadratic"] = ev.get("non_quadratic_results", 0)

        elif event_type == "profiling_end":
            summary["total_rounds"] = ev.get("total_rounds", 0)
            summary["final_linear"] = ev.get("final_constraints_linear", 0)
            summary["final_quadratic"] = ev.get("final_constraints_quadratic", 0)
            summary["final_total"] = ev.get("final_constraints_total", 0)
            summary["signals_deleted"] = ev.get("signals_deleted", 0)
            summary["signals_remaining"] = ev.get("signals_remaining", 0)
            summary["total_duration_ms"] = ev.get("total_duration_ms", 0)

    # Count cluster process usage
    p3_count = 0
    p4_count = 0
    cluster_sizes = []
    for ev in entry["events"]:
        if ev.get("event") == "cluster_simplification":
            cluster_sizes.append(ev.get("cluster_size", 0))
            if ev.get("process") == "process_3":
                p3_count += 1
            elif ev.get("process") == "process_4":
                p4_count += 1
    summary["clusters_process_3"] = p3_count
    summary["clusters_process_4"] = p4_count
    summary["num_clusters"] = len(cluster_sizes)
    if cluster_sizes:
        summary["max_cluster_size"] = max(cluster_sizes)
        summary["avg_cluster_size"] = round(sum(cluster_sizes) / len(cluster_sizes), 1)

    return summary


def print_summary_table(summaries: list[dict]):
    """Print a human-readable summary table."""
    print("\n" + "=" * 120)
    print("PROFILING SUMMARY")
    print("=" * 120)

    header = (
        f"{'File':<30}"
        f"{'Rounds':>7}"
        f"{'EqSub':>6}"
        f"{'CeqSub':>7}"
        f"{'LinSub':>7}"
        f"{'NL->L':>6}"
        f"{'FinalQ':>7}"
        f"{'P3':>4}"
        f"{'P4':>4}"
        f"{'MaxCl':>6}"
        f"{'add':>7}"
        f"{'sub':>7}"
        f"{'mul':>7}"
        f"{'div+':>6}"
        f"{'ms':>8}"
    )
    print(header)
    print("-" * 120)

    for s in summaries:
        if "total_duration_ms" not in s:
            print(f"{s['file'][:29]:<30}{s['status']} (no profiling data)")
            continue

        div_plus = sum(s.get(k, 0) for k in [
            "op_div", "op_idiv", "op_mod", "op_pow",
            "op_shift_l", "op_shift_r", "op_bit_or", "op_bit_and", "op_bit_xor"
        ])

        row = (
            f"{s['file'][:29]:<30}"
            f"{s.get('total_rounds', 0):>7}"
            f"{s.get('eq_subs', 0):>6}"
            f"{s.get('ceq_subs', 0):>7}"
            f"{s.get('lin_subs', 0):>7}"
            f"{s.get('linearized_from_nonlinear', 0):>6}"
            f"{s.get('final_quadratic', 0):>7}"
            f"{s.get('clusters_process_3', 0):>4}"
            f"{s.get('clusters_process_4', 0):>4}"
            f"{s.get('max_cluster_size', '?'):>6}"
            f"{s.get('op_add', 0):>7}"
            f"{s.get('op_sub', 0):>7}"
            f"{s.get('op_mul', 0):>7}"
            f"{div_plus:>6}"
            f"{s.get('total_duration_ms', 0):>7}ms"
        )
        print(row)

    # Aggregate
    print("\n" + "-" * 80)
    print("AGGREGATE:")
    op_keys = ["op_add", "op_sub", "op_mul", "op_div", "op_idiv", "op_mod",
               "op_pow", "op_shift_l", "op_shift_r", "op_bit_or", "op_bit_and", "op_bit_xor"]
    op_labels = ["add", "sub", "mul", "div", "idiv", "mod",
                 "pow", "shift_l", "shift_r", "bit_or", "bit_and", "bit_xor"]
    nonzero_ops = []
    for key, label in zip(op_keys, op_labels):
        total = sum(s.get(key, 0) for s in summaries)
        if total > 0:
            nonzero_ops.append(f"{label}={total}")
    print(f"  Operators: {', '.join(nonzero_ops) if nonzero_ops else '(none)'}")

    total_p3 = sum(s.get("clusters_process_3", 0) for s in summaries)
    total_p4 = sum(s.get("clusters_process_4", 0) for s in summaries)
    total_rounds = sum(s.get("total_rounds", 0) for s in summaries)
    print(f"  Clusters: process_3={total_p3}, process_4={total_p4}")
    print(f"  Optimization rounds: {total_rounds}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Profile Circom compiler simplification on SMT benchmarks")
    parser.add_argument("--benchmarks-dir", type=Path, default=DEFAULT_BENCHMARKS,
                        help="Directory containing .smt2 files")
    parser.add_argument("--max-files", type=int, default=10,
                        help="Maximum number of benchmark files to process")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Timeout per compilation in seconds")
    parser.add_argument("--output", type=Path, default=None,
                        help="Save detailed JSON results to file")
    args = parser.parse_args()

    if not PROFILING_CIRCOM.exists():
        print(f"ERROR: Profiling circom not found at {PROFILING_CIRCOM}")
        print("Run: cd third_party/circom-profiling && cargo build --release")
        sys.exit(1)

    smt2_files = sorted(args.benchmarks_dir.glob("*.smt2"))
    if not smt2_files:
        print(f"No .smt2 files found in {args.benchmarks_dir}")
        sys.exit(1)

    selected = smt2_files[:args.max_files]
    print(f"Processing {len(selected)} benchmarks from {args.benchmarks_dir}")
    print(f"Using profiling circom: {PROFILING_CIRCOM}")

    env = os.environ.copy()

    # Step 1: Convert .smt2 -> .circom
    circom_dir = Path(tempfile.mkdtemp(prefix="profiling_circom_"))
    print(f"\nStep 1: Converting .smt2 -> .circom...")
    circom_files = convert_smt_to_circom(selected, circom_dir, env)
    print(f"  Generated {len(circom_files)} .circom files")

    if not circom_files:
        print("ERROR: No .circom files generated.")
        sys.exit(1)

    # Step 2: Compile each with profiling circom
    print(f"\nStep 2: Compiling with profiling circom (timeout={args.timeout}s)...")
    results = []
    summaries = []

    r1cs_dir = Path(tempfile.mkdtemp(prefix="profiling_r1cs_"))
    for i, circom_file in enumerate(circom_files):
        print(f"  [{i+1}/{len(circom_files)}] {circom_file.name}...", end=" ", flush=True)
        entry = compile_circom(circom_file, CIRCOMLIB_DIR, r1cs_dir, args.timeout)
        results.append(entry)

        summary = extract_summary(entry)
        summaries.append(summary)

        if entry["events"]:
            rounds = summary.get("total_rounds", 0)
            final = summary.get("final_total", "?")
            print(f"rounds={rounds}, final_constraints={final}")
        else:
            print(f"{entry['status']} (no profiling data)")

    print_summary_table(summaries)

    # Cleanup
    shutil.rmtree(circom_dir, ignore_errors=True)
    shutil.rmtree(r1cs_dir, ignore_errors=True)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to {args.output}")


if __name__ == "__main__":
    main()
