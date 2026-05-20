#!/usr/bin/env python3
"""
Analyse SMT artificial-bugs run results.

Usage:
    python3 analyse-smt.py <obj/run-TIMESTAMP-smt-*> [...]

Prints:
  1. Per-instance table: iteration and time to first bug (or Never)
  2. Aggregate stats: bugs/programs and bugs/second
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path


_SOUNDNESS_BUG_ITER_RE = re.compile(r"\[([^\]]+)\]\s+(\d+)/\d+\s+Soundness bug!")
_SOUNDNESS_BUG_DETECTED_RE = re.compile(r"\[([^\]]+)\].*Detected soundness bug!")
_TIMESTAMP_FMT = "%Y/%m/%d %I:%M:%S %p"
_SOLVER_CALLS_RE = re.compile(r"Performed (\d+) solver calls")
_SEEDS_RE = re.compile(r"(\d+) seeds processed")
_BUG_TRIGGERS_RE = re.compile(r"(\d+) bug triggers found")


def _parse_yinyang_log(log_path: Path) -> tuple[int | None, float | None]:
    """Return (bug_iteration, time_to_bug_seconds) from a yinyang log file."""
    if not log_path.exists():
        return None, None

    lines = log_path.read_text(errors="replace").splitlines()
    start_time: datetime | None = None
    bug_iteration: int | None = None
    bug_time: float | None = None

    last_calls_before_bug: int = 0

    for line in lines:
        ts_match = re.match(r"\[([^\]]+)\]", line)
        if ts_match and start_time is None:
            try:
                start_time = datetime.strptime(ts_match.group(1), _TIMESTAMP_FMT)
            except ValueError:
                pass

        # Track solver call count so we can use it as iteration proxy for picus
        calls_match = _SOLVER_CALLS_RE.search(line)
        if calls_match and bug_iteration is None:
            last_calls_before_bug = int(calls_match.group(1))

        # Format 1: "N/total Soundness bug!" (sat/unsat oracle)
        bug_match = _SOUNDNESS_BUG_ITER_RE.search(line)
        if bug_match and bug_iteration is None:
            try:
                bug_time_dt = datetime.strptime(bug_match.group(1), _TIMESTAMP_FMT)
                bug_iteration = int(bug_match.group(2))
                if start_time is not None:
                    bug_time = (bug_time_dt - start_time).total_seconds()
            except (ValueError, TypeError):
                pass

        # Format 2: "Detected soundness bug!" (picus oracle)
        det_match = _SOUNDNESS_BUG_DETECTED_RE.search(line)
        if det_match and bug_iteration is None:
            try:
                bug_time_dt = datetime.strptime(det_match.group(1), _TIMESTAMP_FMT)
                bug_iteration = last_calls_before_bug + 1
                if start_time is not None:
                    bug_time = (bug_time_dt - start_time).total_seconds()
            except (ValueError, TypeError):
                pass

    return bug_iteration, bug_time


def _parse_out_file(out_path: Path) -> tuple[int, bool, float | None]:
    """Return (total_iterations, bug_found_in_out, elapsed_sec) from .out file."""
    if not out_path.exists():
        return 0, False, None
    text = out_path.read_text(errors="replace")

    # Total iterations: seeds processed or last solver calls count
    total = 0
    m = _SEEDS_RE.search(text)
    if m:
        total = int(m.group(1))
    else:
        calls = _SOLVER_CALLS_RE.findall(text)
        total = int(calls[-1]) if calls else 0

    # Bug found in .out
    bug_found = bool(_BUG_TRIGGERS_RE.search(text) and
                     int((_BUG_TRIGGERS_RE.search(text) or re.match(r"0", "0")).group(1)) > 0)

    # Elapsed: parse first and last timestamp
    timestamps = re.findall(r"\[(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} [AP]M)\]", text)
    elapsed: float | None = None
    if len(timestamps) >= 2:
        try:
            t0 = datetime.strptime(timestamps[0], _TIMESTAMP_FMT)
            t1 = datetime.strptime(timestamps[-1], _TIMESTAMP_FMT)
            elapsed = (t1 - t0).total_seconds()
        except ValueError:
            pass

    return total, bug_found, elapsed


def _read_instance(instance_dir: Path) -> dict:
    # Find the result JSON — there's one per instance named <instance_name>.json
    json_files = [f for f in instance_dir.glob("*.json") if f.name != "summary.json"]
    # Derive instance name from directory name or .out file
    out_files = list(instance_dir.glob("*.out"))
    instance_name_fallback = out_files[0].stem if out_files else None

    if not json_files and not instance_name_fallback:
        return {
            "label": instance_dir.name,
            "bug_found": False,
            "bug_iteration": None,
            "time_to_bug": None,
            "total_iterations": 0,
            "total_time": None,
        }

    if not json_files:
        # No JSON (interrupted run) — fall back to .out + logs
        instance_name = instance_name_fallback
        out_path = instance_dir / f"{instance_name}.out"
        total_iterations, bug_found_out, elapsed_out = _parse_out_file(out_path)
        bug_iteration, time_to_bug = None, None
        log_dir = instance_dir / instance_name / "logs"
        if log_dir.exists():
            for log_file in sorted(log_dir.glob("yinyang-*.log")):
                it, t = _parse_yinyang_log(log_file)
                if it is not None:
                    bug_iteration, time_to_bug = it, t
                    break
        return {
            "label": instance_dir.name,
            "bug_found": bug_found_out,
            "bug_iteration": bug_iteration,
            "time_to_bug": time_to_bug,
            "total_iterations": total_iterations,
            "total_time": elapsed_out,
        }

    result_json = json_files[0]
    instance_name = result_json.stem  # e.g. artbugs_bool_sat

    try:
        data = json.loads(result_json.read_text())
    except Exception:
        data = {}

    out_path = instance_dir / f"{instance_name}.out"
    total_iterations_out, bug_found_out, elapsed_out = _parse_out_file(out_path)

    bug_found = data.get("status") == "bugs_found" or bug_found_out
    elapsed_sec: float | None = data.get("elapsed_sec") or elapsed_out

    # Find bug iteration + time-to-bug from yinyang log
    bug_iteration: int | None = None
    time_to_bug: float | None = None
    log_dir = instance_dir / instance_name / "logs"
    if log_dir.exists():
        for log_file in sorted(log_dir.glob("yinyang-*.log")):
            it, t = _parse_yinyang_log(log_file)
            if it is not None:
                bug_iteration = it
                time_to_bug = t
                break

    total_iterations = total_iterations_out

    return {
        "label": instance_dir.name,
        "bug_found": bug_found,
        "bug_iteration": bug_iteration,
        "time_to_bug": time_to_bug,
        "total_iterations": total_iterations,
        "total_time": elapsed_sec,
    }


def _fmt(v: object, decimals: int = 1) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def analyse(run_dir: Path) -> None:
    instance_dirs = sorted(run_dir.glob("instance-*/"))
    if not instance_dirs:
        print(f"[warn] no instance-* dirs found in {run_dir}", file=sys.stderr)
        return

    instances = [_read_instance(d) for d in instance_dirs]

    reports_dir = run_dir.parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"{run_dir.name}.txt"

    lines: list[str] = []

    def emit(s: str = "") -> None:
        print(s)
        lines.append(s)

    # ── Per-instance table ────────────────────────────────────────────────────
    col = dict(label=12, bug_found=10, bug_iter=12, time_to_bug=14, total_iter=14, total_time=12)
    header = (
        f"{'Instance':<{col['label']}}"
        f"{'Bug found':<{col['bug_found']}}"
        f"{'Bug iter':<{col['bug_iter']}}"
        f"{'Time to bug (s)':<{col['time_to_bug']}}"
        f"{'Total iters':<{col['total_iter']}}"
        f"{'Total time (s)':<{col['total_time']}}"
    )
    sep = "─" * len(header)

    emit(f"\n{'═' * len(header)}")
    emit(f"  {run_dir.name}")
    emit(f"{'═' * len(header)}")
    emit(header)
    emit(sep)

    for inst in instances:
        emit(
            f"{inst['label']:<{col['label']}}"
            f"{'yes' if inst['bug_found'] else 'no':<{col['bug_found']}}"
            f"{_fmt(inst['bug_iteration']):<{col['bug_iter']}}"
            f"{_fmt(inst['time_to_bug']) if inst['bug_found'] else 'Never':<{col['time_to_bug']}}"
            f"{_fmt(inst['total_iterations']):<{col['total_iter']}}"
            f"{_fmt(inst['total_time']):<{col['total_time']}}"
        )

    emit(sep)

    # ── Aggregate stats ───────────────────────────────────────────────────────
    total_bugs = sum(1 for i in instances if i["bug_found"])
    total_programs = sum(i["total_iterations"] for i in instances)
    total_time_sum = sum(i["total_time"] for i in instances if i["total_time"] is not None)

    emit()
    emit("  Aggregate")
    emit(f"  {'Instances run:':<28} {len(instances)}")
    emit(f"  {'Bugs found:':<28} {total_bugs} / {len(instances)}")
    emit(f"  {'Total programs tested:':<28} {total_programs}")
    if total_programs > 0:
        emit(f"  {'Bugs / program:':<28} {total_bugs / total_programs:.4f}  ({total_bugs}/{total_programs})")
    if total_time_sum > 0:
        emit(f"  {'Bugs / second:':<28} {total_bugs / total_time_sum:.4f}  (over {total_time_sum:.1f}s total)")
    emit(f"{'═' * len(header)}\n")

    report_path.write_text("\n".join(lines) + "\n")
    print(f"  [report saved to {report_path}]", file=sys.stderr)


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <obj/run-TIMESTAMP-smt-*> [...]", file=sys.stderr)
        return 1

    for arg in sys.argv[1:]:
        run_dir = Path(arg)
        if not run_dir.is_dir():
            print(f"[warn] not a directory: {run_dir}", file=sys.stderr)
            continue
        analyse(run_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
