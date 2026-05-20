#!/usr/bin/env bash
#
# Prepare bool-vs-ff benchmarks.
#
# Picks N random benchmarks that exist in both core/sat (Boolean) and
# finite-field/sat (FF), then copies each set into benchmarks/bool/ and
# benchmarks/ff/ respectively.
#
# Usage: ./prepare.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMT_ROOT="$(realpath "$SCRIPT_DIR/../../smt-solver")"
BOOL_SRC="$SMT_ROOT/benchmarks/core/sat-simple"
FF_SRC="$SMT_ROOT/benchmarks/finite-field/sat"

BOOL_OUT="$SCRIPT_DIR/benchmarks/bool"
FF_OUT="$SCRIPT_DIR/benchmarks/ff"

SEED=42
N=200

# ── Select N files present in both dirs ───────────────────────────────────────

mapfile -t SELECTED < <(python3 - <<EOF
import random, os
random.seed($SEED)
bool_files = set(f for f in os.listdir("$BOOL_SRC") if f.endswith(".smt2"))
ff_files   = set(f for f in os.listdir("$FF_SRC")   if f.endswith(".smt2"))
common = sorted(bool_files & ff_files)
for f in random.sample(common, $N):
    print(f)
EOF
)

echo "Selected $N benchmarks (seed=$SEED)"

mkdir -p "$BOOL_OUT" "$FF_OUT"

for f in "${SELECTED[@]}"; do
    cp "$BOOL_SRC/$f" "$BOOL_OUT/$f"
    cp "$FF_SRC/$f"   "$FF_OUT/$f"
done

echo "Bool benchmarks → $BOOL_OUT"
echo "FF   benchmarks → $FF_OUT"
echo "Done."
