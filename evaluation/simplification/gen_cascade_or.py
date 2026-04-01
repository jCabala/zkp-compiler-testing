#!/usr/bin/env python3
"""
Generate benchmarks using option 3: cascading OR tree.

Builds a deeply nested OR assertion with one always-false anchor:
  (assert (or (or (or (and x1 (not x1)) y1) y2) y3 ...))

No intermediate named variables — avoids IsEqual encoding.
The always-false anchor (x1 AND NOT x1) should be substituted in round 1,
causing the outermost OR to linearise in round 2, and so on.

Usage:
    python gen_cascade_or.py --depth 5 --output benchmarks-multi-round/cascade_or.smt2
    python gen_cascade_or.py --depth 5 --output-dir benchmarks-multi-round --count 3
"""

import argparse
from pathlib import Path


def generate(depth: int, seed: int) -> str:
    lines = [
        f"; cascading OR benchmark (direct nesting) — depth={depth}, seed={seed}",
        "(set-logic QF_BV)",
        "(declare-fun x1 () Bool)",
        "(declare-fun x2 () Bool)",
        "(assert (not x1))",
        "(assert (not x2))",
        "",
        "; y variables — one per OR level",
    ]

    for i in range(1, depth + 1):
        lines.append(f"(declare-fun y{i} () Bool)")

    lines.append("")
    lines.append("; deeply nested OR — no intermediate named variables")
    lines.append("; innermost is always false: (and x1 (not x1))")

    # Build nested OR from inside out: (or (or (or FALSE y1) y2) y3 ...)
    expr = "(and x1 (not x1))"
    for i in range(1, depth + 1):
        expr = f"(or {expr} y{i})"
    lines.append(f"(assert {expr})")

    lines += ["", "(check-sat)", "(get-model)"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate cascading OR benchmarks")
    parser.add_argument("--depth", type=int, default=5,
                        help="Depth of the OR cascade (= number of rounds expected)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Single output file")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory (generates --count files)")
    parser.add_argument("--count", type=int, default=3,
                        help="Number of files to generate (with --output-dir)")
    args = parser.parse_args()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generate(args.depth, seed=0))
        print(f"Written: {args.output}")
    elif args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for i in range(args.count):
            path = args.output_dir / f"cascade_or_{i+1:03d}.smt2"
            path.write_text(generate(args.depth, seed=i))
            print(f"Written: {path}")
    else:
        print(generate(args.depth, seed=0), end="")


if __name__ == "__main__":
    main()


