#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
COVERAGE_ROOT=$(realpath "$SCRIPT_DIR/..")
REPO_ROOT=$(realpath "$SCRIPT_DIR/../../..")

# --- Usage ---
usage() {
  echo "usage: $0 <arithmetic|fully-constraint|all>" >&2
  echo "" >&2
  echo "Runs circuzz with the coverage-instrumented Circom image." >&2
  echo "" >&2
  echo "Variants:" >&2
  echo "  arithmetic        circuzz oracle + normal arithmetic generator" >&2
  echo "  fully-constraint  circuzz oracle + fully-constraint generator" >&2
  echo "  all               run both variants sequentially" >&2
  exit 1
}

VARIANT="${1:-}"
if [[ -z "$VARIANT" ]]; then
  usage
fi

# --- Run both variants in parallel ---
if [[ "$VARIANT" == "all" && "${IN_PODMAN:-0}" != "1" ]]; then
  echo "[coverage] Running all circuzz variants in parallel..." >&2
  "$SCRIPT_DIR/coverage.sh" arithmetic &
  PID_ARITH=$!
  "$SCRIPT_DIR/coverage.sh" fully-constraint &
  PID_FULLY=$!

  FAIL=0
  wait "$PID_ARITH" || FAIL=1
  wait "$PID_FULLY" || FAIL=1
  exit $FAIL
fi

case "$VARIANT" in
  arithmetic)
    CONFIG_FILE="$SCRIPT_DIR/config/circom-arithmetic.json"
    ;;
  fully-constraint)
    CONFIG_FILE="$SCRIPT_DIR/config/circom-fully-constraint.json"
    ;;
  *)
    usage
    ;;
esac

EXPERIMENT_NAME="circuzz-${VARIANT}"
OBJ_DIR="$COVERAGE_ROOT/obj/$EXPERIMENT_NAME"

# --- Experiment parameters ---
CIRCUZZ_SEED="${CIRCUZZ_SEED:-7586}"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-64g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"
DURATION="${DURATION:-60}"  # overall experiment duration in seconds
VERBOSITY="${VERBOSITY:-3}"

IMAGE_CIRCOM_COVERAGE="localhost/circuzz-circom-coverage:latest"

# ---------- HOST MODE ----------
if [[ "${IN_PODMAN:-0}" != "1" ]]; then
  container_name="coverage-circuzz-${VARIANT}-$$"

  podman run --rm \
    --name "$container_name" \
    -v "$REPO_ROOT":/workspace \
    --workdir /workspace/evaluation/coverage/circuzz \
    --memory "$CONTAINER_MEMORY" \
    --memory-swap "$CONTAINER_MEMORY_SWAP" \
    -e IN_PODMAN=1 \
    -e CIRCUZZ_SEED \
    -e DURATION \
    -e VERBOSITY \
    "$IMAGE_CIRCOM_COVERAGE" \
    bash -lc "./coverage.sh $VARIANT"

  exit $?
fi

# ---------- CONTAINER MODE ----------
echo "[preflight] circom=$(which circom)" >&2
echo "[preflight] image=${IMAGE_CIRCOM_COVERAGE}" >&2
echo "[preflight] LLVM_PROFILE_FILE=${LLVM_PROFILE_FILE:-<unset>}" >&2
echo "[preflight] profraw dir: /coverage/profraw" >&2
echo "[preflight] variant: $VARIANT" >&2

if [[ -z "${LLVM_PROFILE_FILE:-}" || ! -d /coverage/profraw ]]; then
  echo "ERROR: coverage environment is not initialized" >&2
  echo "Run this script from the host so it can launch $IMAGE_CIRCOM_COVERAGE" >&2
  exit 1
fi

rm -f /coverage/profraw/*.profraw
mkdir -p "$OBJ_DIR"

# --- Circuzz paths ---
CIRCUZZ_ROOT="/workspace/circuzz"
CIRCUZZ_CLI="$CIRCUZZ_ROOT/cli.py"

# Config path must be relative to circuzz root (cli.py rejects absolute paths)
CONFIG_CONTAINER="../evaluation/coverage/circuzz/config/circom-${VARIANT}.json"

WORKING_DIR="/tmp/circuzz-coverage-${VARIANT}"
REPORT_DIR="$OBJ_DIR/report"
LOG_DIR="$OBJ_DIR/logs"

mkdir -p "$REPORT_DIR" "$LOG_DIR" "$WORKING_DIR"

# Convert DURATION seconds to circuzz HMS format
DURATION_H=$((DURATION / 3600))
DURATION_M=$(((DURATION % 3600) / 60))
DURATION_S=$((DURATION % 60))
CIRCUZZ_TIMEOUT=$(printf "%sh%sm%ss" $DURATION_H $DURATION_M $DURATION_S)

OUT_FILE="$OBJ_DIR/coverage_circuzz.out"

generate_coverage() {
  echo "" >&2
  echo "[coverage] Generating coverage report..." >&2
  bash "$COVERAGE_ROOT/generate_report.sh" "$EXPERIMENT_NAME"
  echo "[coverage] Done. Reports in $COVERAGE_ROOT/obj/$EXPERIMENT_NAME/coverage_report/" >&2
}
trap generate_coverage EXIT

echo "[coverage] Running circuzz ($VARIANT) for ${DURATION}s (Ctrl-C to stop early)..." >&2
echo "[coverage] Config: $CONFIG_CONTAINER" >&2
echo "[coverage] Seed: $CIRCUZZ_SEED" >&2

cd "$CIRCUZZ_ROOT"

python3 "$CIRCUZZ_CLI" explore \
  --tool circom \
  -v"$VERBOSITY" \
  --timeout "$CIRCUZZ_TIMEOUT" \
  --working-dir "$WORKING_DIR" \
  --report-dir "$REPORT_DIR" \
  --seed "$CIRCUZZ_SEED" \
  --config "$CONFIG_CONTAINER" \
  > "$OUT_FILE" 2>&1 &
CIRCUZZ_PID=$!

( sleep "$DURATION" && kill "$CIRCUZZ_PID" 2>/dev/null ) &
TIMER_PID=$!

wait "$CIRCUZZ_PID" 2>/dev/null || true
kill "$TIMER_PID" 2>/dev/null || true
