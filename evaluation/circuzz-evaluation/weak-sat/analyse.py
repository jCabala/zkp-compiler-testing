#!/usr/bin/env python3
"""
Reads one or more Circuzz summary.csv files and prints weak-SAT connectivity
statistics: among circuits where a satisfying witness was found, what fraction
of assertions are connected (depend on an input signal) vs. disconnected.

Usage:
    python3 analyse.py <summary.csv> [<summary.csv> ...]

Expected columns (added to DataEntry in data.py):
    c1_weak_sat_connected    -- int: connected assertion count for C1
    c1_weak_sat_disconnected -- int: disconnected assertion count for C1

SAT is determined per backend:
    circom  -- circom_c1_cpp_witness_generation == True
               OR circom_c1_js_witness_generation == True
    gnark   -- gnark_c1_witness_solved == True
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

TOOL_COL = "tool"
C1_CONNECTED_COL = "c1_weak_sat_connected"
C1_DISCONNECTED_COL = "c1_weak_sat_disconnected"

CIRCOM_SAT_COLS = ["circom_c1_cpp_witness_generation", "circom_c1_js_witness_generation"]
GNARK_SAT_COL = "gnark_c1_witness_solved"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def is_sat(row: dict[str, str]) -> bool:
    tool = row.get(TOOL_COL, "").strip().strip('"')
    if tool == "circom":
        return any(
            row.get(col, "").strip().strip('"') == "True"
            for col in CIRCOM_SAT_COLS
        )
    if tool == "gnark":
        return row.get(GNARK_SAT_COL, "").strip().strip('"') == "True"
    return False


def _parse_int(val: str) -> int | None:
    v = val.strip().strip('"')
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def compute_stats(rows: list[dict[str, str]]) -> dict[str, dict]:
    # per-tool: total_sat_circuits, total_connected, total_disconnected
    stats: dict[str, dict] = defaultdict(
        lambda: {"sat_circuits": 0, "connected": 0, "disconnected": 0}
    )
    for row in rows:
        if not is_sat(row):
            continue
        connected = _parse_int(row.get(C1_CONNECTED_COL, ""))
        disconnected = _parse_int(row.get(C1_DISCONNECTED_COL, ""))
        if connected is None or disconnected is None:
            continue
        tool = row.get(TOOL_COL, "unknown").strip().strip('"')
        stats[tool]["sat_circuits"] += 1
        stats[tool]["connected"] += connected
        stats[tool]["disconnected"] += disconnected
    return stats


def print_table(stats: dict[str, dict]) -> None:
    col_w = 20
    header = (
        f"{'Backend':<12}"
        f"{'SAT circuits':>{col_w}}"
        f"{'Total assertions':>{col_w}}"
        f"{'Connected':>{col_w}}"
        f"{'Disconnected':>{col_w}}"
        f"{'% Disconnected':>{col_w}}"
    )
    print(header)
    print("-" * len(header))

    for tool in sorted(stats):
        s = stats[tool]
        total = s["connected"] + s["disconnected"]
        pct_disc = 100 * s["disconnected"] / total if total else 0.0
        print(
            f"{tool:<12}"
            f"{s['sat_circuits']:>{col_w}}"
            f"{total:>{col_w}}"
            f"{s['connected']:>{col_w}}"
            f"{s['disconnected']:>{col_w}}"
            f"{pct_disc:>{col_w-1}.1f}%"
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
        if rows and C1_CONNECTED_COL not in rows[0]:
            print(
                f"WARNING: '{C1_CONNECTED_COL}' column not found in {path}. "
                "Make sure the CSV was produced with the updated data.py.",
                file=sys.stderr,
            )
        all_rows.extend(rows)

    stats = compute_stats(all_rows)
    if not stats:
        print("No SAT rows with weak-SAT data found.")
        return 0

    print_table(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
