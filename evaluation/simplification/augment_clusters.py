#!/usr/bin/env python3
"""
Augment .smt2 benchmarks with a NOT chain anchored to the most frequent variable,
artificially enlarging the largest linear cluster to trigger P4 (threshold: 350).

Usage:
    python augment_clusters.py input.smt2 output.smt2 --chain-length 400
    python augment_clusters.py --input-dir DIR --output-dir DIR --chain-length 400
"""

import argparse
import re
from collections import Counter
from pathlib import Path


def find_most_frequent_variable(smt2: str) -> str:
    """Find the variable with the highest occurrence count in assertions."""
    # Match all xN variable references in assertions
    variables = re.findall(r'\bx\d+\b', smt2)
    counts = Counter(variables)
    return counts.most_common(1)[0][0]


def augment_smt2(smt2: str, chain_length: int) -> str:
    """
    Inject a NOT chain of given length anchored to the most frequent variable.
    The chain is always satisfiable — c_i values are fully determined by the anchor.
    """
    anchor = find_most_frequent_variable(smt2)

    declarations = "\n".join(
        f"(declare-fun c{i} () Bool)" for i in range(1, chain_length + 1)
    )

    # c1 anchors to the most frequent existing variable
    assertions = [f"(assert (= c1 (not {anchor})))"]
    for i in range(2, chain_length + 1):
        assertions.append(f"(assert (= c{i} (not c{i - 1})))")
    assertions_str = "\n".join(assertions)

    injection = f"\n; --- NOT chain: {chain_length} links anchored to {anchor} ---\n{declarations}\n{assertions_str}\n"

    # Insert before (check-sat)
    return smt2.replace("(check-sat)", injection + "(check-sat)", 1)


def process_file(input_path: Path, output_path: Path, chain_length: int):
    smt2 = input_path.read_text()
    augmented = augment_smt2(smt2, chain_length)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(augmented)
    anchor = find_most_frequent_variable(smt2)
    print(f"  {input_path.name} -> {output_path.name}  (anchor={anchor}, chain={chain_length})")


def main():
    parser = argparse.ArgumentParser(description="Augment .smt2 files with a NOT chain to enlarge linear clusters")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("input", nargs="?", type=Path, help="Single input .smt2 file")
    parser.add_argument("output", nargs="?", type=Path, help="Single output .smt2 file")
    group.add_argument("--input-dir", type=Path, help="Directory of .smt2 files to augment")
    parser.add_argument("--output-dir", type=Path, help="Output directory (required with --input-dir)")
    parser.add_argument("--chain-length", type=int, default=400,
                        help="Length of the NOT chain to inject (default: 400, P4 threshold is 350)")
    parser.add_argument("--max-files", type=int, default=None,
                        help="Maximum number of files to process (for --input-dir)")
    args = parser.parse_args()

    if args.input_dir:
        if not args.output_dir:
            parser.error("--output-dir is required when using --input-dir")
        smt2_files = sorted(args.input_dir.glob("*.smt2"))
        if args.max_files:
            smt2_files = smt2_files[:args.max_files]
        print(f"Augmenting {len(smt2_files)} files from {args.input_dir}")
        for f in smt2_files:
            process_file(f, args.output_dir / f.name, args.chain_length)
        print(f"Done. Written to {args.output_dir}")
    else:
        if not args.output:
            parser.error("output path is required for single-file mode")
        process_file(args.input, args.output, args.chain_length)


if __name__ == "__main__":
    main()
