#!/usr/bin/env python3
"""
Merge all individual reports into a single MASTER report.

Usage:
    python3 merge-reports.py

Reads all *.txt reports (except MASTER.txt) from the reports/ directory,
groups them by experiment type, appends per-group aggregates, and writes
reports/MASTER.txt.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"
MASTER_PATH = REPORTS_DIR / "MAIN.txt"

# Maps filename fragment → display group name
GROUP_ORDER = [
    ("smt-bool-sat",    "SMT — Bool SAT"),
    ("smt-bool-unsat",  "SMT — Bool UNSAT"),
    ("smt-bool-picus",  "SMT — Bool PICUS"),
    ("smt-ff-sat",      "SMT — FF SAT"),
    ("smt-ff-unsat",    "SMT — FF UNSAT"),
    ("smt-ff-picus",    "SMT — FF PICUS"),
    ("circuzz-standard","Circuzz — Standard"),
    ("circuzz-picus",   "Circuzz — Picus"),
]

# Regexes to extract per-instance rows and aggregate lines from report text
_INSTANCE_ROW_RE = re.compile(
    r"^(instance-\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$"
)
_BUGS_FOUND_RE    = re.compile(r"Bugs found:\s+(\d+) / (\d+)")
_TOTAL_PROG_RE    = re.compile(r"Total programs tested:\s+(\d+)")
_TOTAL_TIME_RE    = re.compile(r"over ([\d.]+)s total")


def _parse_report(path: Path) -> dict:
    text = path.read_text()
    bugs_m     = _BUGS_FOUND_RE.search(text)
    prog_m     = _TOTAL_PROG_RE.search(text)
    time_m     = _TOTAL_TIME_RE.search(text)
    return {
        "name":           path.stem,
        "text":           text,
        "bugs":           int(bugs_m.group(1))   if bugs_m  else 0,
        "instances":      int(bugs_m.group(2))   if bugs_m  else 0,
        "total_programs": int(prog_m.group(1))   if prog_m  else 0,
        "total_time":     float(time_m.group(1)) if time_m  else 0.0,
    }


def _group_aggregate(reports: list[dict]) -> str:
    total_bugs     = sum(r["bugs"]           for r in reports)
    total_inst     = sum(r["instances"]      for r in reports)
    total_programs = sum(r["total_programs"] for r in reports)
    total_time     = sum(r["total_time"]     for r in reports)

    lines = [
        "  ── Group aggregate ──────────────────────────────",
        f"  {'Runs:':<28} {len(reports)}",
        f"  {'Instances total:':<28} {total_inst}",
        f"  {'Bugs found:':<28} {total_bugs} / {total_inst}",
        f"  {'Total programs tested:':<28} {total_programs}",
    ]
    if total_programs > 0:
        lines.append(
            f"  {'Bugs / program:':<28} "
            f"{total_bugs / total_programs:.4f}  ({total_bugs}/{total_programs})"
        )
    if total_time > 0:
        lines.append(
            f"  {'Bugs / second:':<28} "
            f"{total_bugs / total_time:.4f}  (over {total_time:.1f}s total)"
        )
    return "\n".join(lines)


def main() -> int:
    report_files = sorted(
        p for p in REPORTS_DIR.glob("*.txt") if p.name != "MAIN.txt"
    )
    if not report_files:
        print("No reports found.", file=sys.stderr)
        return 1

    reports = [_parse_report(p) for p in report_files]

    # Group reports
    groups: dict[str, list[dict]] = {}
    ungrouped: list[dict] = []
    for r in reports:
        placed = False
        for key, label in GROUP_ORDER:
            if key in r["name"]:
                groups.setdefault(label, []).append(r)
                placed = True
                break
        if not placed:
            ungrouped.append(r)

    output: list[str] = []
    width = 79

    output.append("═" * width)
    output.append("  MAIN REPORT — Artificial Bugs Evaluation")
    output.append("═" * width)
    output.append("")

    for _key, label in GROUP_ORDER:
        group = groups.get(label, [])
        if not group:
            continue

        output.append("┌" + "─" * (width - 2) + "┐")
        output.append(f"│  {label:<{width - 4}}│")
        output.append("└" + "─" * (width - 2) + "┘")
        output.append("")

        for r in group:
            # Strip leading/trailing blank lines from individual report
            output.append(r["text"].strip())
            output.append("")

        output.append(_group_aggregate(group))
        output.append("")
        output.append("─" * width)
        output.append("")

    if ungrouped:
        output.append("┌" + "─" * (width - 2) + "┐")
        output.append(f"│  {'Other':<{width - 4}}│")
        output.append("└" + "─" * (width - 2) + "┘")
        output.append("")
        for r in ungrouped:
            output.append(r["text"].strip())
            output.append("")

    # Overall aggregate
    total_bugs     = sum(r["bugs"]           for r in reports)
    total_inst     = sum(r["instances"]      for r in reports)
    total_programs = sum(r["total_programs"] for r in reports)
    total_time     = sum(r["total_time"]     for r in reports)

    output.append("═" * width)
    output.append("  OVERALL AGGREGATE")
    output.append("─" * width)
    output.append(f"  {'Runs:':<28} {len(reports)}")
    output.append(f"  {'Instances total:':<28} {total_inst}")
    output.append(f"  {'Bugs found:':<28} {total_bugs} / {total_inst}")
    output.append(f"  {'Total programs tested:':<28} {total_programs}")
    if total_programs > 0:
        output.append(
            f"  {'Bugs / program:':<28} "
            f"{total_bugs / total_programs:.4f}  ({total_bugs}/{total_programs})"
        )
    if total_time > 0:
        output.append(
            f"  {'Bugs / second:':<28} "
            f"{total_bugs / total_time:.4f}  (over {total_time:.1f}s total)"
        )
    output.append("═" * width)

    master_text = "\n".join(output) + "\n"
    MASTER_PATH.write_text(master_text)
    print(master_text)
    print(f"  [master report saved to {MASTER_PATH}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
