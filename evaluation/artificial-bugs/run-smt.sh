#!/usr/bin/env bash
#
# Run N parallel SMT artificial-bugs instances locally (no podman).
#
# Usage:
#   ./run-smt.sh <bool|ff> <sat|unsat|picus>
#
# Each instance runs with a different yinyang seed.
#
# Override examples:
#   N_INSTANCES=3 ./run-smt.sh ff sat

set -euo pipefail

BENCHMARK="${1:-}"
ORACLE="${2:-}"

if [[ -z "$BENCHMARK" || -z "$ORACLE" ]]; then
    echo "Usage: $0 <bool|ff> <sat|unsat|picus>"
    exit 1
fi

case "$BENCHMARK" in
    bool|ff) ;;
    *) echo "Unknown benchmark '$BENCHMARK'. Choose: bool | ff"; exit 1 ;;
esac

case "$ORACLE" in
    sat|unsat|picus) ;;
    *) echo "Unknown oracle '$ORACLE'. Choose: sat | unsat | picus"; exit 1 ;;
esac

INSTANCE_NAME="artbugs_${BENCHMARK}_${ORACLE}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "$SCRIPT_DIR/../..")"
SMT_ROOT="$REPO_ROOT/smt-solver"
ARTBUGS_BIN="$SMT_ROOT/third_party/artificial-bugs/circom/target/release/circom"
CONFIG="$SMT_ROOT/experiments/configs/artbugs_${BENCHMARK}.json"

N_INSTANCES="${N_INSTANCES:-1}"
SEEDS=(7586 12345 67890 11111 99999 55555 77777 33333 21212 98765)

# ── Preflight ─────────────────────────────────────────────────────────────────

if [[ ! -x "$ARTBUGS_BIN" ]]; then
    echo "[error] artbugs binary not found at: $ARTBUGS_BIN"
    echo "Build: cd $SMT_ROOT/third_party/artificial-bugs/circom && cargo build --release"
    exit 1
fi
if ! "$ARTBUGS_BIN" --help 2>&1 | grep -q "artificial-bugs-build"; then
    echo "[error] binary at $ARTBUGS_BIN is missing the 'artificial-bugs-build' marker"
    exit 1
fi

# ── Output directory ──────────────────────────────────────────────────────────

START=$(date +%s)
OBJ_DIR="$SCRIPT_DIR/obj/run-${START}-smt-${BENCHMARK}-${ORACLE}"
mkdir -p "$OBJ_DIR"
echo "smt-${BENCHMARK}" > "$OBJ_DIR/tool.txt"

echo "[preflight] instance:  $INSTANCE_NAME"
echo "[preflight] instances: $N_INSTANCES"
echo "[preflight] config:    $CONFIG"
echo "[preflight] output:    $OBJ_DIR"
echo ""

# ── Spawn instances ───────────────────────────────────────────────────────────

PIDS=()

for (( i=0; i<N_INSTANCES; i++ )); do
    seed="${SEEDS[$i]}"
    instance_dir="$OBJ_DIR/instance-${i}"
    mkdir -p "$instance_dir"

    echo "  Spawning instance $i  (seed=$seed)"
    python3 "$SMT_ROOT/experiments/run_experiments.py" \
        --config "$CONFIG" \
        --output-dir "$instance_dir" \
        --artifacts-dir "$instance_dir" \
        --instance-name "$INSTANCE_NAME" \
        --yinyang-seed "$seed" \
        --local \
        2>&1 | tee "$instance_dir/run.log" &
    PIDS+=($!)
done

trap 'echo "Interrupted"; kill "${PIDS[@]}" 2>/dev/null; exit 1' INT TERM

echo ""
echo "All $N_INSTANCES instances running..."
echo ""

python3 "$SCRIPT_DIR/watch.py" "$OBJ_DIR" &
WATCH_PID=$!

for pid in "${PIDS[@]}"; do
    wait "$pid" || true
done

wait "$WATCH_PID" 2>/dev/null || true

echo ""
echo "════════════════════════════════════════"
echo "  Done. Results: $OBJ_DIR"
echo "════════════════════════════════════════"
