#!/usr/bin/env python3
"""Analyse benchmark-size throughput results and save a report.

Usage:
  python3 analyse.py <results.json> [<results.json> ...]

Report saved to: reports/report-{timestamp}.txt
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = SCRIPT_DIR / "reports"


def load(path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(path.read_text())
    return data.get("metadata", {}), data["results"]


def format_table(meta: dict, results: list[dict]) -> str:
    lines = []
    lines.append(f"Config: hints={meta.get('hints')}  dsl={meta.get('dsl')}  solver={meta.get('solver')}  timeout={meta.get('timeout')}s")
    lines.append(f"Source: {meta.get('source', 'n/a')}")
    lines.append("")

    by_vars: dict[int, list[dict]] = defaultdict(list)
    for r in results:
        by_vars[r["vars"]].append(r)

    hdr = f"  {'Vars':>6}  {'N':>4}  {'Mean sat (s)':>14}  {'Min (s)':>10}  {'Max (s)':>10}  {'Timeout/Unk%':>14}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))
    for v in sorted(by_vars):
        rows = by_vars[v]
        n = len(rows)
        sat_times = [r["elapsed_sec"] for r in rows if r["result"] == "sat"]
        n_bad = sum(1 for r in rows if r["result"] in {"timeout", "unknown"})
        pct_bad = 100 * n_bad / n if n else 0.0
        mean_s = f"{sum(sat_times)/len(sat_times):>10.3f}" if sat_times else f"{'—':>10}"
        min_s  = f"{min(sat_times):>10.3f}"               if sat_times else f"{'—':>10}"
        max_s  = f"{max(sat_times):>10.3f}"               if sat_times else f"{'—':>10}"
        lines.append(f"  {v:>6}  {n:>4}  {mean_s:>14}  {min_s:>10}  {max_s:>10}  {pct_bad:>13.1f}%")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <results.json> [<results.json> ...]", file=sys.stderr)
        sys.exit(1)

    sections = []
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        meta, results = load(path)
        meta["source"] = str(path)
        sections.append(format_table(meta, results))

    report_body = "\n\n".join(sections)

    print(report_body)

    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"report-{int(time.time())}.txt"
    report_path.write_text(report_body + "\n")
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
