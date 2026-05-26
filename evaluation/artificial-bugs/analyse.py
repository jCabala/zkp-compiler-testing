#!/usr/bin/env python3
"""
Analyse artificial-bugs experiment results.

Usage:
    python3 analyse.py <obj/run-TIMESTAMP>

Reads:
  smt/artbugs_*.json        -- run_experiments.py result per instance
  smt/artbugs_*.out         -- yinyang stdout/stderr (contains iteration counts)
  circuzz/report/summary.csv -- circuzz per-circuit data (iteration, error)
  circuzz/report/.done       -- circuzz wall-clock time for the whole run

Prints a table:
  Experiment | Oracle | Benchmark | Bug found | Iterations | Time (s)
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


# ── SMT-solver (yinyang) ─────────────────────────────────────────────────────

def _parse_yinyang_out(out_path: Path) -> int | None:
    """Return the iteration index of the first detected soundness bug, or None."""
    if not out_path.exists():
        return None
    pattern = re.compile(r"(\d+)/\d+\s+Soundness bug!")
    for line in out_path.read_text(errors="replace").splitlines():
        m = pattern.search(line)
        if m:
            return int(m.group(1))
    return None


def _load_smt_results(smt_dir: Path) -> list[dict]:
    rows = []
    for json_path in sorted(smt_dir.glob("*.json")):
        if json_path.name == "summary.json":
            continue
        try:
            data = json.loads(json_path.read_text())
        except Exception:
            continue

        name = data.get("name", json_path.stem)
        elapsed = data.get("elapsed_sec")
        status = data.get("status", "unknown")
        bug_found = status == "bugs_found"

        out_path = smt_dir / f"{name}.out"
        first_iteration = _parse_yinyang_out(out_path)

        # Derive benchmark and oracle label from instance name
        # Convention: artbugs_{bool|ff}_{sat|unsat|picus}
        parts = name.split("_")
        benchmark = parts[1] if len(parts) > 1 else "?"
        oracle = parts[2] if len(parts) > 2 else "?"

        rows.append({
            "experiment": "smt-solver",
            "benchmark": benchmark,
            "oracle": oracle,
            "bug_found": bug_found,
            "first_iteration": first_iteration,
            "elapsed_sec": elapsed,
        })
    return rows


# ── Circuzz ──────────────────────────────────────────────────────────────────

def _load_circuzz_results(circuzz_report: Path) -> dict:
    done_path = circuzz_report / ".done"
    summary_path = circuzz_report / "summary.csv"

    elapsed: float | None = None
    if done_path.exists():
        for line in done_path.read_text().splitlines():
            if line.startswith("time:"):
                try:
                    elapsed = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

    first_iteration: int | None = None
    bug_found = False
    if summary_path.exists():
        try:
            with summary_path.open(newline="") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    error = row.get("error", "").strip().strip('"')
                    if error and error.lower() not in ("none", ""):
                        bug_found = True
                        # Use row index as proxy for circuit count if iteration column absent
                        try:
                            first_iteration = int(row.get("iteration", idx))
                        except (ValueError, TypeError):
                            first_iteration = idx
                        break
        except Exception:
            pass

    return {
        "experiment": "circuzz",
        "benchmark": "circuzz-fully-constrained",
        "oracle": "?",
        "bug_found": bug_found,
        "first_iteration": first_iteration,
        "elapsed_sec": elapsed,
    }


# ── Formatting ────────────────────────────────────────────────────────────────

def _fmt(value: object, default: str = "n/a") -> str:
    if value is None:
        return default
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def print_table(rows: list[dict]) -> None:
    col_widths = {
        "experiment":     12,
        "benchmark":      28,
        "oracle":          8,
        "bug_found":      10,
        "first_iteration": 12,
        "elapsed_sec":    12,
    }
    headers = {
        "experiment":     "Experiment",
        "benchmark":      "Benchmark",
        "oracle":         "Oracle",
        "bug_found":      "Bug found",
        "first_iteration": "Iteration",
        "elapsed_sec":    "Time (s)",
    }

    def row_str(r: dict) -> str:
        return (
            f"{r.get('experiment',''):<{col_widths['experiment']}}"
            f"{r.get('benchmark',''):<{col_widths['benchmark']}}"
            f"{r.get('oracle',''):<{col_widths['oracle']}}"
            f"{'yes' if r.get('bug_found') else 'no':<{col_widths['bug_found']}}"
            f"{_fmt(r.get('first_iteration')):<{col_widths['first_iteration']}}"
            f"{_fmt(r.get('elapsed_sec')):<{col_widths['elapsed_sec']}}"
        )

    header = (
        f"{'Experiment':<{col_widths['experiment']}}"
        f"{'Benchmark':<{col_widths['benchmark']}}"
        f"{'Oracle':<{col_widths['oracle']}}"
        f"{'Bug found':<{col_widths['bug_found']}}"
        f"{'Iteration':<{col_widths['first_iteration']}}"
        f"{'Time (s)':<{col_widths['elapsed_sec']}}"
    )
    sep = "-" * len(header)

    print(header)
    print(sep)
    for r in rows:
        print(row_str(r))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <obj/run-TIMESTAMP>", file=sys.stderr)
        return 1

    run_dir = Path(sys.argv[1])
    if not run_dir.is_dir():
        print(f"Not a directory: {run_dir}", file=sys.stderr)
        return 1

    rows: list[dict] = []

    smt_dir = run_dir / "smt"
    if smt_dir.is_dir():
        rows.extend(_load_smt_results(smt_dir))
    else:
        print(f"[warn] no smt dir found at {smt_dir}", file=sys.stderr)

    for label, oracle in (("picus", "picus"), ("standard", "circuzz")):
        circuzz_report = run_dir / f"circuzz-{label}" / "report"
        if circuzz_report.is_dir():
            row = _load_circuzz_results(circuzz_report)
            row["benchmark"] = f"circuzz-fully-constrained"
            row["oracle"] = oracle
            rows.append(row)
        else:
            print(f"[warn] no circuzz-{label} report dir found at {circuzz_report}", file=sys.stderr)

    if not rows:
        print("No results found.")
        return 1

    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
