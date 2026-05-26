#!/usr/bin/env python3
"""Plot mean solve time vs variable count for multiple results.json files.

Timeouts and unknowns are counted at the configured timeout value so the
mean includes all benchmarks (no survivor bias).

Usage:
  python3 plot.py <results.json> [<results.json> ...]

Output saved to reports/plot-{timestamp}.pdf (and .png).
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = SCRIPT_DIR / "reports"


def load(path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(path.read_text())
    return data.get("metadata", {}), data["results"]


def compute_series(results: list[dict], timeout: int) -> tuple[list[int], list[float]]:
    by_vars: dict[int, list[float]] = defaultdict(list)
    for r in results:
        if r["result"] in {"timeout", "unknown"}:
            by_vars[r["vars"]].append(float(timeout))
        else:
            by_vars[r["vars"]].append(r["elapsed_sec"])
    all_vars = sorted(by_vars)
    means = [sum(by_vars[v]) / len(by_vars[v]) for v in all_vars]
    return all_vars, means


def label(meta: dict) -> str:
    hints = "hints=on" if meta.get("hints") else "hints=off"
    return f"{hints}, {meta.get('dsl')}, {meta.get('solver')}"


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <results.json> [<results.json> ...]", file=sys.stderr)
        sys.exit(1)

    fig, ax = plt.subplots(figsize=(8, 5))

    for path_str in sys.argv[1:]:
        meta, results = load(Path(path_str))
        timeout = meta.get("timeout", 60)
        xs, ys = compute_series(results, timeout)
        ax.plot(xs, ys, marker="o", label=label(meta))

    # dotted line at the timeout value (use the first file's timeout)
    if sys.argv[1:]:
        first_meta, _ = load(Path(sys.argv[1]))
        timeout_val = first_meta.get("timeout", 60)
        ax.axhline(timeout_val, color="red", linestyle=":", linewidth=1, label=f"timeout ({timeout_val}s)")

    ax.set_xlabel("Seed variable count $n$ (fused formula has $2n+1$ to $3n$ variables)")
    ax.set_ylabel("Mean solve time (s)")
    ax.set_title("Benchmark size vs. solve time")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    REPORTS_DIR.mkdir(exist_ok=True)
    ts = int(time.time())
    for ext in ("pdf", "png"):
        out = REPORTS_DIR / f"plot-{ts}.{ext}"
        fig.savefig(out, bbox_inches="tight")
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
