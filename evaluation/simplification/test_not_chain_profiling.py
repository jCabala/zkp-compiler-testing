#!/usr/bin/env python3
"""
Test the smt-solver CLI with NOT chain injection and profiling compiler.

For each benchmark:
  1. Runs `solve` with --not-chain-length, --max-not-chain-count, and --with-logs.
     --with-logs causes the CLI to save the augmented .circom (chains injected) to disk.
  2. Compiles that saved .circom directly with the profiling compiler to capture
     simplification statistics from stderr (P3/P4 counts, rounds, cluster sizes).
  3. Reports whether P4 was triggered (requires cluster_size >= 350) and how many rounds.

Two passes are run per file: baseline (no chains) vs augmented (chains injected),
so the effect of NOT chain injection is directly visible.

Usage:
    python test_not_chain_profiling.py \\
        [--benchmarks-dir DIR] [--max-files N] \\
        [--not-chain-length N] [--max-not-chain-count N] \\
        [--solver z3|cvc5] [--timeout SECS] [--output results.json]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPT_DIR.parent.parent
SMT_SOLVER_DIR = REPO_ROOT / "smt-solver"
PROFILING_CIRCOM = SCRIPT_DIR / "third_party" / "circom-profiling" / "target" / "release" / "circom"
DEFAULT_BENCHMARKS = SMT_SOLVER_DIR / "benchmarks" / "SMT-benchmarks" / "core" / "unique_sat_1to5vars"
CIRCOMLIB_DIR = SMT_SOLVER_DIR / "experiments" / "circomlib"
LOG_FILE = SCRIPT_DIR / "test_not_chain_profiling.log"

P4_THRESHOLD = 350  # minimum cluster size to trigger P4


def append_log(section: str, content: str) -> None:
    """Append a timestamp-free log section to a persistent file next to this script."""
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 100}\n")
        f.write(section)
        f.write("\n")
        f.write(f"{'=' * 100}\n")
        f.write(content)
        if not content.endswith("\n"):
            f.write("\n")


# ---------------------------------------------------------------------------
# CLI invocation
# ---------------------------------------------------------------------------

def run_solve(
    smt2_path: Path,
    work_dir: Path,
    compiler: Path,
    not_chain_length: int,
    max_not_chain_count: int,
    solver: str,
    timeout: int,
    env: dict,
) -> Path | None:
    """
    Run the `solve` CLI on smt2_path with NOT chain injection and --with-logs.
    The CLI saves the augmented .circom to work_dir/{stem}_converted.circom.
    Returns the path to the saved .circom, or None on failure.
    """
    # Copy .smt2 into work_dir so the CLI saves the debug .circom there
    smt2_copy = work_dir / smt2_path.name
    shutil.copy(smt2_path, smt2_copy)

    cmd = [
        sys.executable, "cli.py", "solve", str(smt2_copy),
        "--zk-dsl", "circom",
        "--solver", solver,
        "--no-simplify",
        "--with-logs",              # causes the CLI to write {stem}_converted.circom
        "--compiler", str(compiler),
        "--not-chain-length", str(not_chain_length),
        "--max-not-chain-count", str(max_not_chain_count),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(SMT_SOLVER_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"    [timeout] solve command exceeded {timeout}s")
        append_log(
            f"SOLVE TIMEOUT [{smt2_path.name}]",
            f"Command timed out after {timeout}s\n"
            f"Compiler: {compiler}\n"
            f"Chain length: {not_chain_length}\n"
            f"Max chain count: {max_not_chain_count}\n"
            f"Solver: {solver}\n",
        )
        return None

    append_log(
        f"SOLVE [{smt2_path.name}] chains={max_not_chain_count} length={not_chain_length}",
        f"Command: {' '.join(cmd)}\n"
        f"Return code: {result.returncode}\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}\n",
    )

    if result.returncode != 0:
        print(f"    [error] solve failed (exit {result.returncode}): {result.stderr[:300]}")
        return None

    circom_path = work_dir / f"{smt2_path.stem}_converted.circom"
    if not circom_path.exists():
        print(f"    [error] expected .circom not found at {circom_path}")
        return None

    return circom_path


# ---------------------------------------------------------------------------
# Profiling compilation
# ---------------------------------------------------------------------------

def compile_with_profiling(
    circom_path: Path,
    out_dir: Path,
    compiler: Path,
    timeout: int,
) -> dict:
    """Compile circom_path with the profiling binary; return parsed profiling data."""
    cmd = [
        str(compiler), str(circom_path),
        "--r1cs", "--O2",
        "-l", str(CIRCOMLIB_DIR),
        "-o", str(out_dir),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        append_log(
            f"PROFILING TIMEOUT [{circom_path.name}]",
            f"Command: {' '.join(cmd)}\n"
            f"Timeout: {timeout}s\n"
            f"--- STDERR ---\n{stderr}\n",
        )
        return {"status": "timeout", "events": _parse_events(stderr)}

    append_log(
        f"PROFILING [{circom_path.name}]",
        f"Command: {' '.join(cmd)}\n"
        f"Return code: {result.returncode}\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}\n",
    )

    events = _parse_events(result.stderr)
    status = "ok" if result.returncode == 0 else f"error (exit {result.returncode})"
    return {"status": status, "events": events}


def _parse_events(stderr: str) -> list[dict]:
    events = []
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def _extract_stats(profiling: dict) -> dict:
    """Collapse profiling events into a flat stats dict."""
    stats: dict = {"status": profiling["status"]}
    p3 = p4 = 0
    cluster_sizes = []
    total_rounds = 0

    for ev in profiling["events"]:
        t = ev.get("event", "")
        if t == "profiling_end":
            stats["total_rounds"]    = ev.get("total_rounds", 0)
            stats["final_linear"]    = ev.get("final_constraints_linear", 0)
            stats["final_quadratic"] = ev.get("final_constraints_quadratic", 0)
            stats["duration_ms"]     = ev.get("total_duration_ms", 0)
            total_rounds = stats["total_rounds"]
        elif t == "cluster_simplification":
            sz = ev.get("cluster_size", 0)
            cluster_sizes.append(sz)
            if ev.get("process") == "process_3":
                p3 += 1
            elif ev.get("process") == "process_4":
                p4 += 1

    stats["clusters_p3"]     = p3
    stats["clusters_p4"]     = p4
    stats["max_cluster"]     = max(cluster_sizes, default=0)
    stats["p4_triggered"]    = p4 > 0
    stats["total_rounds"]    = total_rounds
    return stats


# ---------------------------------------------------------------------------
# Comparison run
# ---------------------------------------------------------------------------

def profile_file(
    smt2_path: Path,
    compiler: Path,
    not_chain_length: int,
    max_not_chain_count: int,
    solver: str,
    timeout: int,
    env: dict,
) -> dict:
    """Run baseline and augmented passes on a single .smt2 file."""
    result = {"file": smt2_path.name}

    with tempfile.TemporaryDirectory(prefix="ncp_") as tmp:
        tmp_path = Path(tmp)
        out_dir  = tmp_path / "r1cs"
        out_dir.mkdir()

        # --- Baseline (no chains) ---
        baseline_dir = tmp_path / "baseline"
        baseline_dir.mkdir()
        circom_baseline = run_solve(
            smt2_path, baseline_dir, compiler,
            not_chain_length=not_chain_length, max_not_chain_count=0,
            solver=solver, timeout=timeout, env=env,
        )
        if circom_baseline:
            prof = compile_with_profiling(circom_baseline, out_dir, compiler, timeout)
            result["baseline"] = _extract_stats(prof)
        else:
            result["baseline"] = {"status": "failed"}

        # --- Augmented (with chains) ---
        aug_dir = tmp_path / "augmented"
        aug_dir.mkdir()
        circom_aug = run_solve(
            smt2_path, aug_dir, compiler,
            not_chain_length=not_chain_length, max_not_chain_count=max_not_chain_count,
            solver=solver, timeout=timeout, env=env,
        )
        if circom_aug:
            prof = compile_with_profiling(circom_aug, out_dir, compiler, timeout)
            result["augmented"] = _extract_stats(prof)
        else:
            result["augmented"] = {"status": "failed"}

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(results: list[dict], not_chain_length: int):
    print("\n" + "=" * 110)
    print(f"NOT CHAIN PROFILING REPORT  (chain_length={not_chain_length}, P4 threshold={P4_THRESHOLD})")
    print("=" * 110)

    header = (
        f"{'File':<35}"
        f"{'-- BASELINE --':^30}"
        f"{'-- AUGMENTED --':^30}"
        f"{'P4 triggered?':>14}"
    )
    sub = (
        f"{'':35}"
        f"{'P3':>5}{'P4':>5}{'MaxCl':>7}{'Rnd':>5}{'ms':>8}"
        f"{'P3':>5}{'P4':>5}{'MaxCl':>7}{'Rnd':>5}{'ms':>8}"
    )
    print(header)
    print(sub)
    print("-" * 110)

    p4_triggered = 0
    for r in results:
        b = r.get("baseline", {})
        a = r.get("augmented", {})

        def fmt(s: dict) -> str:
            if s.get("status") in ("failed", "timeout"):
                return f"{'':>5}{'':>5}  {s.get('status','?'):<16}"
            return (
                f"{s.get('clusters_p3', 0):>5}"
                f"{s.get('clusters_p4', 0):>5}"
                f"{s.get('max_cluster', 0):>7}"
                f"{s.get('total_rounds', 0):>5}"
                f"{s.get('duration_ms', 0):>7}ms"
            )

        triggered = a.get("p4_triggered", False)
        if triggered:
            p4_triggered += 1

        print(
            f"{r['file'][:34]:<35}"
            f"{fmt(b):<30}"
            f"{fmt(a):<30}"
            f"{'YES ✓' if triggered else 'no':>14}"
        )

    print("=" * 110)
    print(f"P4 triggered in {p4_triggered}/{len(results)} augmented benchmarks")

    # Sanity check
    failed_to_trigger = [
        r["file"] for r in results
        if r.get("augmented", {}).get("status") == "ok"
        and not r.get("augmented", {}).get("p4_triggered", False)
    ]
    if failed_to_trigger:
        print(f"\nWARNING: P4 not triggered despite chains in {len(failed_to_trigger)} file(s):")
        for f in failed_to_trigger:
            aug = next(r["augmented"] for r in results if r["file"] == f)
            print(f"  {f}  max_cluster={aug.get('max_cluster', '?')} (need >={P4_THRESHOLD})")
        print("  → Chain may not have merged into existing cluster; check anchor connectivity.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    LOG_FILE.write_text("", encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Test NOT chain injection via the smt-solver CLI with profiling circom"
    )
    parser.add_argument("--benchmarks-dir", type=Path, default=DEFAULT_BENCHMARKS)
    parser.add_argument("--pattern",             default="*.smt2",
                        help="Glob pattern to filter benchmark files (default: *.smt2). E.g. 'unique[3-5]*.smt2'")
    parser.add_argument("--max-files",           type=int,  default=10)
    parser.add_argument("--not-chain-length",    type=int,  default=400,
                        help="Length of each injected NOT chain (default: 400)")
    parser.add_argument("--max-not-chain-count", type=int,  default=3,
                        help="Max number of chains to inject per benchmark (default: 3)")
    parser.add_argument("--solver",              default="z3", choices=["z3", "cvc5"])
    parser.add_argument("--timeout",             type=int,  default=60,
                        help="Per-file timeout in seconds")
    parser.add_argument("--output",              type=Path, default=None,
                        help="Save full JSON results to file")
    parser.add_argument("--compiler",            type=Path, default=PROFILING_CIRCOM,
                        help=f"Profiling circom binary (default: {PROFILING_CIRCOM})")
    args = parser.parse_args()

    if not args.compiler.exists():
        print(f"ERROR: Compiler not found at {args.compiler}")
        print("Build it with:  cd evaluation/simplification/third_party/circom-profiling && cargo build --release")
        sys.exit(1)

    smt2_files = sorted(args.benchmarks_dir.glob(args.pattern))[:args.max_files]
    if not smt2_files:
        print(f"No .smt2 files found in {args.benchmarks_dir}")
        sys.exit(1)

    print(f"Benchmarks : {args.benchmarks_dir} ({len(smt2_files)} files)")
    print(f"Compiler   : {args.compiler}")
    print(f"Chain      : length={args.not_chain_length}, max_count={args.max_not_chain_count}")
    print(f"Solver     : {args.solver}  Timeout: {args.timeout}s\n")
    print(f"Log file   : {LOG_FILE}")

    env = os.environ.copy()
    results = []

    for i, smt2 in enumerate(smt2_files):
        print(f"[{i+1}/{len(smt2_files)}] {smt2.name}")
        entry = profile_file(
            smt2, args.compiler,
            args.not_chain_length, args.max_not_chain_count,
            args.solver, args.timeout, env,
        )
        results.append(entry)
        b, a = entry.get("baseline", {}), entry.get("augmented", {})
        print(f"  baseline : P4={b.get('clusters_p4', '?')}, max_cluster={b.get('max_cluster', '?')}")
        print(f"  augmented: P4={a.get('clusters_p4', '?')}, max_cluster={a.get('max_cluster', '?')}, p4_triggered={a.get('p4_triggered', '?')}")

    print_report(results, args.not_chain_length)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2))
        print(f"Full results saved to {args.output}")


if __name__ == "__main__":
    main()
