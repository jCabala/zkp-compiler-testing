#!/usr/bin/env bash
#
# Compile all bool-circom and ff-circom benchmarks to R1CS JSON.
#
# Output:
#   r1cs/bool/   ← R1CS JSON from Boolean Circom
#   r1cs/ff/     ← R1CS JSON from FF Circom
#
# Usage: ./compile.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMT_ROOT="$(realpath "$SCRIPT_DIR/../../smt-solver")"

BOOL_IN="$SCRIPT_DIR/benchmarks/bool-circom"
FF_IN="$SCRIPT_DIR/benchmarks/ff-circom"
BOOL_OUT="$SCRIPT_DIR/r1cs/bool"
FF_OUT="$SCRIPT_DIR/r1cs/ff"

mkdir -p "$BOOL_OUT" "$FF_OUT"

compile_dir() {
    local in_dir="$1"
    local out_dir="$2"
    local label="$3"
    local ok=0 fail=0

    echo "=== Compiling $label ==="
    for f in "$in_dir"/*.circom; do
        name="$(basename "$f" .circom)"
        out="$out_dir/$name.r1cs.json"
        if (cd "$SMT_ROOT" && python3 cli.py export-r1cs-command "$f" -o "$out" 2>/dev/null); then
            (( ok++ )) || true
        else
            echo "  FAILED: $(basename "$f")"
            (( fail++ )) || true
        fi
    done
    echo "  ok=$ok  failed=$fail"
    echo ""
}

compile_dir "$BOOL_IN" "$BOOL_OUT" "bool-circom"
compile_dir "$FF_IN"   "$FF_OUT"   "ff-circom"

echo "Bool R1CS → $BOOL_OUT  ($(ls "$BOOL_OUT" | wc -l) files)"
echo "FF   R1CS → $FF_OUT    ($(ls "$FF_OUT"   | wc -l) files)"
echo "Done."
