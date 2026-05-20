#!/usr/bin/env bash
#
# Prepare padded (non-simplified) benchmark variants.
#
# Same as prepare.sh but skips the simplification step.
# Output: benchmarks/padded/vars-01/ ... benchmarks/padded/vars-19/
#
# Usage: ./prepare-padded.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMT_ROOT="$(realpath "$SCRIPT_DIR/../../smt-solver")"
SEEDS_DIR="$SMT_ROOT/benchmarks/seeds/uf-20-sat"
OUT_DIR="$SCRIPT_DIR/benchmarks/padded"

SEED=42
N_BENCHMARKS=5
MAX_VARS=19

# ── Select the same 5 files as prepare.sh ────────────────────────────────────

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

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

STAGE_DIR="$TMP_DIR/stage"
mkdir -p "$STAGE_DIR"
for f in "${SELECTED[@]}"; do
    cp "$f" "$STAGE_DIR/"
done

mkdir -p "$OUT_DIR"

# ── For each k, prune only (no simplify) ─────────────────────────────────────

for k in $(seq 1 $MAX_VARS); do
    KDIR=$(printf "vars-%02d" $k)
    FINAL_DIR="$OUT_DIR/$KDIR"

    mkdir -p "$FINAL_DIR"

    echo "=== vars=$k → padded/$KDIR ==="

    python3 "$SMT_ROOT/cli.py" prune-smtlib2-folder \
        --k "$k" \
        --seed "$SEED" \
        "$STAGE_DIR" "$FINAL_DIR"
done

echo ""
echo "Done. Padded benchmarks written to $OUT_DIR"
