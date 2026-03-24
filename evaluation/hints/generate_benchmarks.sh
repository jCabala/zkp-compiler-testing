#!/usr/bin/env bash
# Generate pruned SMT-LIB benchmarks for hints evaluation.
# Run from the repo root or inside the smt-solver container.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SMT_SOLVER="$REPO_ROOT/smt-solver"
SOURCE_DIR="$SCRIPT_DIR/source"
BENCHMARKS="$SMT_SOLVER/benchmarks/SMT-benchmarks/core/sat"

# 1. Copy source files
mkdir -p "$SOURCE_DIR"
for f in uf20-010 uf20-0100 uf20-01000 uf20-0101 uf20-0102; do
    cp "$BENCHMARKS/${f}.smt2" "$SOURCE_DIR/"
done
echo "Copied 5 source benchmarks to $SOURCE_DIR"

# 2. Prune at each k level
for k in 5 10 15; do
    out="$SCRIPT_DIR/k${k}"
    echo "Pruning to k=$k -> $out"
    python3 "$SMT_SOLVER/cli.py" prune-smtlib2-folder "$SOURCE_DIR" "$out" --k "$k" --seed 0 --solver z3
done

# k=20 matches original variable count, so just copy the sources
echo "Copying originals as k=20 (no pruning needed)"
mkdir -p "$SCRIPT_DIR/k20"
cp "$SOURCE_DIR"/*.smt2 "$SCRIPT_DIR/k20/"

echo "Done. Benchmarks in $SCRIPT_DIR/k{5,10,15,20}/"
