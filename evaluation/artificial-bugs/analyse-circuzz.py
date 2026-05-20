#!/usr/bin/env python3
"""
Analyse circuzz artificial-bugs run results.

Usage:
    python3 analyse-circuzz.py <obj/run-TIMESTAMP-circuzz-*> [...]

Prints:
  1. Per-instance table: iteration and time to first bug (or Never)
  2. Aggregate stats: bugs/programs and bugs/second
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def _read_instance(instance_dir: Path) -> dict:
    report = instance_dir / "circuzz" / "report"
    summary = report / "summary.csv"
    done = report / ".done"

    total_elapsed: float | None = None
    if done.exists():
        for line in done.read_text().splitlines():
            if line.startswith("time:"):
                try:
                    total_elapsed = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

    if not summary.exists():
        return {
            "label": instance_dir.name,
            "bug_found": False,
            "bug_iteration": None,
            "time_to_bug": None,
            "total_iterations": 0,
            "total_time": total_elapsed,
        }

    bug_iteration: int | None = None
    time_to_bug: float | None = None
    total_iterations = 0

    with summary.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_iterations += 1
            if bug_iteration is None:
                error = (row.get("error") or "").strip().strip('"')
                if error and error.lower() not in ("none", ""):
                    try:
                        bug_iteration = int(row.get("iteration") or total_iterations - 1)
                    except (ValueError, TypeError):
                        bug_iteration = total_iterations - 1
                    try:
                        time_to_bug = float(row.get("explore_time") or 0)
                    except (ValueError, TypeError):
                        time_to_bug = None

    return {
        "label": instance_dir.name,
        "bug_found": bug_iteration is not None,
        "bug_iteration": bug_iteration,
        "time_to_bug": time_to_bug,
        "total_iterations": total_iterations,
        "total_time": total_elapsed if total_elapsed is not None else cumulative_time,
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
        print(f"Usage: {sys.argv[0]} <obj/run-TIMESTAMP-circuzz-*> [...]", file=sys.stderr)
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
