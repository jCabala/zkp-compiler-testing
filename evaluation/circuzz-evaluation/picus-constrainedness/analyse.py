#!/usr/bin/env python3
"""
Reads one or more Circuzz summary.csv files produced by a Picus-oracle run and
prints a constrainedness distribution table per backend.

Usage:
    python3 analyse.py <summary.csv> [<summary.csv> ...]

Expected columns in each CSV (added to DataEntry in data.py):
    picus_transformed_constraint_level  -- fully_constrained | under_constrained | inconclusive | ...
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path


LEVEL_COL = "picus_transformed_constraint_level"
TOOL_COL = "tool"


def has_variables(row: dict[str, str]) -> bool:
    inputs = int(row.get("c1_input_signals", "0") or "0")
    outputs = int(row.get("c1_output_signals", "0") or "0")
    return inputs + outputs > 0


def count_levels(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, int]], int]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    excluded = 0
    for row in rows:
        if not has_variables(row):
            excluded += 1
            continue
        level = row.get(LEVEL_COL, "").strip().strip('"') or "not_recorded"
        tool = row.get(TOOL_COL, "unknown").strip().strip('"')
        counts[tool][level] += 1
    return counts, excluded


def print_table(counts: dict[str, dict[str, int]]) -> None:
    all_levels = sorted({lv for tool_counts in counts.values() for lv in tool_counts})
    col_w = 22

    header = f"{'Backend':<12}" + "".join(f"{lv:>{col_w}}" for lv in all_levels) + f"{'Total':>{col_w}}"
    print(header)
    print("-" * len(header))

    for tool in sorted(counts):
        tool_counts = counts[tool]
        total = sum(tool_counts.values())
        row = f"{tool:<12}"
        for lv in all_levels:
            n = tool_counts.get(lv, 0)
            pct = 100 * n / total if total else 0
            cell = f"{n} ({pct:.1f}%)"
            row += cell.rjust(col_w)
        row += str(total).rjust(col_w)
        print(row)


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <summary.csv> [<summary.csv> ...]", file=sys.stderr)
        return 1

    all_rows: list[dict[str, str]] = []
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if LEVEL_COL not in headers:
                print(
                    f"WARNING: '{LEVEL_COL}' column not found in {path}. "
                    "Make sure the CSV was produced with the updated data.py.",
                    file=sys.stderr,
                )
            rows = list(reader)
        if not rows:
            print(f"NOTE: {path} has 0 data rows (experiment may have timed out before completing any test).", file=sys.stderr)
        all_rows.extend(rows)

    counts, excluded = count_levels(all_rows)
    if excluded:
        print(f"(Excluded {excluded} program(s) with no variables)\n")
    print_table(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
