#!/usr/bin/env python3
"""
Watch an artificial-bugs run directory and print a fresh report whenever
any result file changes.  Auto-detects which tool was run from tool.txt.

Usage:
    python3 watch.py <obj/run-TIMESTAMP-TOOL>

Exits automatically when the experiment is complete.
Press Ctrl-C to stop watching early (the background process keeps running).
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

POLL_INTERVAL = 5  # seconds


# ── Result extraction ─────────────────────────────────────────────────────────

def _parse_first_soundness_bug(out_path: Path) -> int | None:
    pattern = re.compile(r"(\d+)/\d+\s+Soundness bug!")
    try:
        for line in out_path.read_text(errors="replace").splitlines():
            m = pattern.search(line)
            if m:
                return int(m.group(1))
    except OSError:
        pass
    return None


def _smt_result(run_dir: Path, name: str) -> dict:
    parts = name.split("_")
    benchmark = parts[1] if len(parts) > 1 else "?"
    oracle    = parts[2] if len(parts) > 2 else "?"

    json_path = run_dir / "smt" / f"{name}.json"
    out_path  = run_dir / "smt" / f"{name}.out"

    elapsed, bug_found, first_iter = None, False, None
    complete = json_path.exists()

    if complete:
        try:
            data      = json.loads(json_path.read_text())
            elapsed   = data.get("elapsed_sec")
            bug_found = data.get("status") == "bugs_found"
        except Exception:
            pass

    first_iter = _parse_first_soundness_bug(out_path)
    if first_iter is not None:
        bug_found = True

    return {
        "experiment": "smt-solver", "benchmark": benchmark, "oracle": oracle,
        "bug_found": bug_found, "first_iteration": first_iter,
        "elapsed_sec": elapsed, "complete": complete,
    }


def _circuzz_result(run_dir: Path, oracle_label: str) -> dict:
    report    = run_dir / "circuzz" / "report"
    done_path = report / ".done"
    summary   = report / "summary.csv"

    elapsed, bug_found, first_iter = None, False, None
    complete = done_path.exists()

    if complete:
        for line in done_path.read_text().splitlines():
            if line.startswith("time:"):
                try:
                    elapsed = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

    if summary.exists():
        try:
            with summary.open(newline="") as f:
                for idx, row in enumerate(csv.DictReader(f)):
                    error = row.get("error", "").strip().strip('"')
                    if error and error.lower() not in ("none", ""):
                        bug_found = True
                        try:
                            first_iter = int(row.get("iteration", idx))
                        except (ValueError, TypeError):
                            first_iter = idx
                        break
        except Exception:
            pass

    return {
        "experiment": "circuzz", "benchmark": "circuzz-fully-constrained",
        "oracle": oracle_label, "bug_found": bug_found,
        "first_iteration": first_iter, "elapsed_sec": elapsed, "complete": complete,
    }


# ── Auto-detect what to watch ─────────────────────────────────────────────────

SMT_BOOL_INSTANCES  = ["artbugs_bool_sat", "artbugs_bool_unsat", "artbugs_bool_picus"]
SMT_FF_INSTANCES    = ["artbugs_ff_sat",   "artbugs_ff_unsat",   "artbugs_ff_picus"]

def _circuzz_instance_result(run_dir: Path, instance_dir: Path, oracle_label: str) -> dict:
    """Like _circuzz_result but reads from instance_dir/circuzz/report."""
    report    = instance_dir / "circuzz" / "report"
    done_path = report / ".done"
    summary   = report / "summary.csv"

    elapsed, bug_found, first_iter = None, False, None
    complete = done_path.exists()

    if complete:
        for line in done_path.read_text().splitlines():
            if line.startswith("time:"):
                try:
                    elapsed = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

    if summary.exists():
        try:
            with summary.open(newline="") as f:
                for idx, row in enumerate(csv.DictReader(f)):
                    error = row.get("error", "").strip().strip('"')
                    if error and error.lower() not in ("none", ""):
                        bug_found = True
                        try:
                            first_iter = int(row.get("iteration", idx))
                        except (ValueError, TypeError):
                            first_iter = idx
                        break
        except Exception:
            pass

    label = instance_dir.name  # e.g. "instance-0"
    return {
        "experiment": f"circuzz ({label})", "benchmark": "circuzz-fully-constrained",
        "oracle": oracle_label, "bug_found": bug_found,
        "first_iteration": first_iter, "elapsed_sec": elapsed, "complete": complete,
    }


def _build_collectors(run_dir: Path) -> list:
    tool = (run_dir / "tool.txt").read_text().strip() if (run_dir / "tool.txt").exists() else ""

    collectors = []
    if tool == "smt-bool":
        for name in SMT_BOOL_INSTANCES:
            collectors.append(lambda d, n=name: _smt_result(d, n))
    elif tool == "smt-ff":
        for name in SMT_FF_INSTANCES:
            collectors.append(lambda d, n=name: _smt_result(d, n))
    elif tool in ("circuzz-picus", "circuzz-standard"):
        oracle = "picus" if tool == "circuzz-picus" else "circuzz"
        # Multi-instance layout: instance-0/, instance-1/, ...
        instance_dirs = sorted(run_dir.glob("instance-*/"))
        if instance_dirs:
            for inst_dir in instance_dirs:
                collectors.append(lambda d, p=inst_dir, o=oracle: _circuzz_instance_result(d, p, o))
        else:
            # Single-instance legacy layout: circuzz/report/
            collectors.append(lambda d, o=oracle: _circuzz_result(d, o))
    else:
        # Unknown tool — try to detect from what exists
        smt_dir = run_dir / "smt"
        if smt_dir.exists():
            names = [p.stem for p in smt_dir.glob("artbugs_*.out")]
            for name in sorted(names):
                collectors.append(lambda d, n=name: _smt_result(d, n))
        instance_dirs = sorted(run_dir.glob("instance-*/"))
        if instance_dirs:
            for inst_dir in instance_dirs:
                collectors.append(lambda d, p=inst_dir: _circuzz_instance_result(d, p, "?"))
        elif (run_dir / "circuzz").exists():
            collectors.append(lambda d: _circuzz_result(d, "?"))
    return collectors


# ── Fingerprint ───────────────────────────────────────────────────────────────

def _fingerprint(run_dir: Path) -> tuple:
    sizes = []
    for p in sorted(run_dir.rglob("*.json")) + sorted(run_dir.rglob("*.out")) \
           + sorted(run_dir.rglob(".done")) + sorted(run_dir.rglob("summary.csv")):
        try:
            sizes.append((str(p), p.stat().st_size))
        except OSError:
            sizes.append((str(p), -1))
    return tuple(sizes)


# ── Table ─────────────────────────────────────────────────────────────────────

def _fmt(v: object) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def _print_table(rows: list[dict], ts: str) -> None:
    cw = dict(experiment=12, benchmark=28, oracle=10,
              bug_found=10, first_iteration=12, elapsed_sec=12, complete=10)
    header = (
        f"{'Experiment':<{cw['experiment']}}"
        f"{'Benchmark':<{cw['benchmark']}}"
        f"{'Oracle':<{cw['oracle']}}"
        f"{'Bug found':<{cw['bug_found']}}"
        f"{'Iteration':<{cw['first_iteration']}}"
        f"{'Time (s)':<{cw['elapsed_sec']}}"
        f"{'Status':<{cw['complete']}}"
    )
    sep = "-" * len(header)
    print(f"\n{'='*len(header)}")
    print(f"  {ts}")
    print(f"{'='*len(header)}")
    print(header)
    print(sep)
    for r in rows:
        status = "done" if r["complete"] else "running"
        print(
            f"{r['experiment']:<{cw['experiment']}}"
            f"{r['benchmark']:<{cw['benchmark']}}"
            f"{r['oracle']:<{cw['oracle']}}"
            f"{'yes' if r['bug_found'] else 'no':<{cw['bug_found']}}"
            f"{_fmt(r['first_iteration']):<{cw['first_iteration']}}"
            f"{_fmt(r['elapsed_sec']):<{cw['elapsed_sec']}}"
            f"{status:<{cw['complete']}}"
        )
    done  = sum(1 for r in rows if r["complete"])
    total = len(rows)
    print(sep)
    print(f"  {done}/{total} complete", flush=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <obj/run-TIMESTAMP-TOOL>", file=sys.stderr)
        return 1
    run_dir = Path(sys.argv[1])
    if not run_dir.is_dir():
        print(f"Not a directory: {run_dir}", file=sys.stderr)
        return 1

    collectors = _build_collectors(run_dir)
    if not collectors:
        print(f"[warn] could not detect any experiments in {run_dir}", file=sys.stderr)
        return 1

    tool = (run_dir / "tool.txt").read_text().strip() if (run_dir / "tool.txt").exists() else "?"
    print(f"Watching {run_dir}  [tool={tool}]  (poll every {POLL_INTERVAL}s — Ctrl-C to stop)")

    containers_file = run_dir / "containers.txt"

    def _container_names() -> list[str]:
        if not containers_file.exists():
            return []
        return [n for n in containers_file.read_text().splitlines() if n]

    def _stop_instance(label: str) -> None:
        # label is e.g. "instance-2" — index maps to containers.txt line
        try:
            idx = int(label.split("-")[1])
            names = _container_names()
            if idx < len(names):
                subprocess.run(["podman", "stop", names[idx]], capture_output=True)
                print(f"  Stopped container for {label}.")
        except (ValueError, IndexError):
            pass

    last_fp = None
    prev_bug_found: set[str] = set()
    while True:
        fp = _fingerprint(run_dir)
        if fp != last_fp:
            last_fp = fp
            rows = [c(run_dir) for c in collectors]
            _print_table(rows, time.strftime("%H:%M:%S"))
            for r in rows:
                label = r["experiment"]  # e.g. "circuzz (instance-2)"
                if r["bug_found"] and label not in prev_bug_found:
                    prev_bug_found.add(label)
                    # Extract "instance-N" from label
                    match = re.search(r"instance-\d+", label)
                    if match:
                        print(f"\nBug found in {match.group()} — stopping that instance.")
                        _stop_instance(match.group())
            if all(r["complete"] for r in rows):
                print("\nExperiment complete.")
                return 0
        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nWatcher stopped.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
