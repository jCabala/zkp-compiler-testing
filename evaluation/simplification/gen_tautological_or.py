#!/usr/bin/env python3
"""
Generate benchmarks using option 1: tautological forcing.

Injects a variable d = (x1 AND NOT(x1)) which is always false,
then asserts (OR d y_i) for each of n extra variables y_i.
Each OR has one side forced to 0, so round 1 linearises them all
into round 2 constraints (or_out = y_i).

Usage:
    python gen_tautological_or.py --or-count 5 --output benchmarks-multi-round/taut_or.smt2
    python gen_tautological_or.py --or-count 5 --output-dir benchmarks-multi-round --count 3
"""

import argparse
from pathlib import Path


def generate(or_count: int, seed: int) -> str:
    lines = [
        f"; tautological OR benchmark — {or_count} ORs, seed={seed}",
        "(set-logic QF_BV)",
        "(declare-fun x1 () Bool)",
        "(declare-fun x2 () Bool)",
        "(assert (not x1))",
        "(assert (not x2))",
        "",
        "; d is always false: x1 AND (NOT x1) = 0",
        "(declare-fun d () Bool)",
        "(assert (= d (and x1 (not x1))))",
        "",
        "; y variables — free, ORed with the always-false d",
    ]

    for i in range(1, or_count + 1):
        lines.append(f"(declare-fun y{i} () Bool)")

    lines.append("")
    lines.append("; OR(d, y_i) — d=0 forces linearisation in round 2")
    for i in range(1, or_count + 1):
        lines.append(f"(assert (or d y{i}))")

    lines += ["", "(check-sat)", "(get-model)"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate tautological OR benchmarks")
    parser.add_argument("--or-count", type=int, default=5,
                        help="Number of OR(d, y_i) assertions to add")
    parser.add_argument("--output", type=Path, default=None,
                        help="Single output file")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory (generates --count files)")
    parser.add_argument("--count", type=int, default=3,
                        help="Number of files to generate (with --output-dir)")
    args = parser.parse_args()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generate(args.or_count, seed=0))
        print(f"Written: {args.output}")
    elif args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for i in range(args.count):
            path = args.output_dir / f"taut_or_{i+1:03d}.smt2"
            path.write_text(generate(args.or_count, seed=i))
            print(f"Written: {path}")
    else:
        print(generate(args.or_count, seed=0), end="")


if __name__ == "__main__":
    main()
