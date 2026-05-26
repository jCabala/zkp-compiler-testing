#!/usr/bin/env bash
#
# Translate bool and ff benchmarks into Circom.
#
# Output:
#   benchmarks/bool-circom/   ← Circom from Boolean SMT2
#   benchmarks/ff-circom/     ← Circom from FF SMT2
#
# Usage: ./translate.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMT_ROOT="$(realpath "$SCRIPT_DIR/../../smt-solver")"

BOOL_IN="$SCRIPT_DIR/benchmarks/bool"
FF_IN="$SCRIPT_DIR/benchmarks/ff"
BOOL_OUT="$SCRIPT_DIR/benchmarks/bool-circom"
FF_OUT="$SCRIPT_DIR/benchmarks/ff-circom"

mkdir -p "$BOOL_OUT" "$FF_OUT"

echo "=== Translating Boolean → Circom ==="
python3 "$SMT_ROOT/cli.py" smt-to-dsl --dsl circom "$BOOL_IN" "$BOOL_OUT"

echo ""
echo "=== Translating FF → Circom ==="
python3 "$SMT_ROOT/cli.py" smt-to-dsl --dsl circom "$FF_IN" "$FF_OUT"

echo ""
echo "Bool-Circom → $BOOL_OUT  ($(ls "$BOOL_OUT" | wc -l) files)"
echo "FF-Circom   → $FF_OUT    ($(ls "$FF_OUT"   | wc -l) files)"
echo "Done."
