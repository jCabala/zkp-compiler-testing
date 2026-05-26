#!/usr/bin/env bash
#
# Prepare benchmark-size experiment benchmarks.
#
# Picks N_BENCHMARKS random uf-20-sat seed files, then for each k in 1..MAX_VARS
# produces a simplified benchmark with exactly k variables.
#
# Output: benchmarks/vars-01/ ... benchmarks/vars-20/
# Each directory contains N_BENCHMARKS simplified SMT2 files.
#
# Usage: ./prepare.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMT_ROOT="$(realpath "$SCRIPT_DIR/../../smt-solver")"
SEEDS_DIR="$SMT_ROOT/benchmarks/seeds/uf-20-sat"
OUT_DIR="$SCRIPT_DIR/benchmarks"

SEED=42
N_BENCHMARKS=5
MAX_VARS=20

# ── Select N_BENCHMARKS files reproducibly ────────────────────────────────────

mapfile -t SELECTED < <(python3 - <<EOF
import random, os
random.seed($SEED)
files = sorted(f for f in os.listdir("$SEEDS_DIR") if f.endswith(".smt2"))
for f in random.sample(files, $N_BENCHMARKS):
    print("$SEEDS_DIR/" + f)
EOF
)

echo "Selected benchmarks:"
for f in "${SELECTED[@]}"; do
    echo "  $(basename "$f")"
done
echo ""

# ── Staging area with just the 5 selected files ───────────────────────────────

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

STAGE_DIR="$TMP_DIR/stage"
mkdir -p "$STAGE_DIR"
for f in "${SELECTED[@]}"; do
    cp "$f" "$STAGE_DIR/"
done

mkdir -p "$OUT_DIR"

# ── For each k, prune then simplify ───────────────────────────────────────────

for k in $(seq 1 $MAX_VARS); do
    KDIR=$(printf "vars-%02d" $k)
    PRUNE_DIR="$TMP_DIR/pruned-$k"
    FINAL_DIR="$OUT_DIR/$KDIR"

    mkdir -p "$PRUNE_DIR" "$FINAL_DIR"

    echo "=== vars=$k → $KDIR ==="

    python3 "$SMT_ROOT/cli.py" prune-smtlib2-folder \
        --k "$k" \
        --seed "$SEED" \
        "$STAGE_DIR" "$PRUNE_DIR"

    python3 "$SMT_ROOT/cli.py" simplify-smtlib2-folder \
        "$PRUNE_DIR" "$FINAL_DIR"
done

echo ""
echo "Done. Benchmarks written to $OUT_DIR"
