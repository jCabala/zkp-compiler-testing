#!/usr/bin/env python3
"""
Reads one or more Circuzz summary.csv files and prints throughput statistics:
average time per test, tests per second, and relative throughput vs the Circom
baseline.

Usage:
    python3 analyse.py <summary.csv> [<summary.csv> ...]

Uses the 'test_time' and 'tool' columns, which are always present in summary.csv.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

TOOL_COL = "tool"
TIME_COL = "test_time"
BASELINE_TOOL = "circom"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def compute_stats(rows: list[dict[str, str]]) -> dict[str, dict]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        tool = row.get(TOOL_COL, "").strip().strip('"')
        raw = row.get(TIME_COL, "").strip().strip('"')
        try:
            t = float(raw)
        except (ValueError, TypeError):
            continue
        if tool and t > 0:
            buckets[tool].append(t)

    stats = {}
    for tool, times in buckets.items():
        avg = sum(times) / len(times)
        stats[tool] = {
            "count": len(times),
            "avg_time": avg,
            "tests_per_sec": 1.0 / avg,
        }
    return stats


def print_table(stats: dict[str, dict]) -> None:
    baseline_tps = stats.get(BASELINE_TOOL, {}).get("tests_per_sec")

    col_w = 18
    header = (
        f"{'Backend':<12}"
        f"{'Tests run':>{col_w}}"
        f"{'Avg time/test':>{col_w}}"
        f"{'Tests/sec':>{col_w}}"
        f"{'Rel. throughput':>{col_w}}"
    )
    print(header)
    print("-" * len(header))

    # Print circom first, then gnark, then others (e.g. mina)
    order = [BASELINE_TOOL, "gnark"] + sorted(
        t for t in stats if t not in (BASELINE_TOOL, "gnark")
    )
    for tool in order:
        if tool not in stats:
            continue
        s = stats[tool]
        rel = s["tests_per_sec"] / baseline_tps if baseline_tps else float("nan")
        print(
            f"{tool:<12}"
            f"{s['count']:>{col_w}}"
            f"{s['avg_time']:>{col_w-1}.2f}s"
            f"{s['tests_per_sec']:>{col_w}.4f}"
            f"{rel:>{col_w}.3f}x"
        )


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
        rows = load_csv(path)
        if rows and TIME_COL not in rows[0]:
            print(f"WARNING: '{TIME_COL}' column not found in {path}.", file=sys.stderr)
        all_rows.extend(rows)

    stats = compute_stats(all_rows)
    if not stats:
        print("No valid rows found.")
        return 0

    print_table(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
