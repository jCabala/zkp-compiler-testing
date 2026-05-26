#!/usr/bin/env bash
#
# Run benchmark-size throughput experiment with and without hints, in parallel.
#
# Usage:
#   ./run-all.sh [--dsl circom|gnark|noir|zokrates] [--benchmarks-dir <path>] [--timeout <secs>]
#
# Defaults: --dsl circom, benchmarks-dir=./benchmarks, timeout=60
#
# Examples:
#   ./run-all.sh
#   ./run-all.sh --dsl gnark
#   ./run-all.sh --dsl circom --benchmarks-dir benchmarks/padded
#   ./run-all.sh --dsl gnark  --benchmarks-dir benchmarks/yinyang

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DSL="circom"
BENCHMARKS_DIR="$SCRIPT_DIR/benchmarks"
TIMEOUT=60

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dsl)            DSL="$2";            shift 2 ;;
        --benchmarks-dir) BENCHMARKS_DIR="$2"; shift 2 ;;
        --timeout)        TIMEOUT="$2";        shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "dsl=$DSL  benchmarks-dir=$BENCHMARKS_DIR  timeout=${TIMEOUT}s"
echo ""

python3 "$SCRIPT_DIR/run.py" --hints    --dsl "$DSL" --solver cvc5 --timeout "$TIMEOUT" --benchmarks-dir "$BENCHMARKS_DIR" &
HINTS_PID=$!

python3 "$SCRIPT_DIR/run.py" --no-hints --dsl "$DSL" --solver cvc5 --timeout "$TIMEOUT" --benchmarks-dir "$BENCHMARKS_DIR" &
NO_HINTS_PID=$!

trap 'kill $HINTS_PID $NO_HINTS_PID 2>/dev/null; exit 1' INT TERM

wait $HINTS_PID    && echo "hints=on  done" || echo "hints=on  failed"
wait $NO_HINTS_PID && echo "hints=off done" || echo "hints=off failed"
