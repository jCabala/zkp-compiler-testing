#!/usr/bin/env bash
#
# Run the Picus constrainedness experiment for 10 minutes on both Circom and
# Gnark backends (concurrently), then produce a constrainedness distribution
# report.
#
# Usage: ./run.sh [--build]
#   --build  rebuild the Podman images before running (default: use existing)
#
# Must be run from anywhere; all paths are resolved relative to this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$SCRIPT_DIR"
CIRCUZZ_DIR="$(realpath "$SCRIPT_DIR/../../../circuzz")"
ANALYSE="$EVAL_DIR/analyse.py"

SEED=2003
START=$(date +%s)
OBJ_DIR_SUFFIX="seed-$SEED-date-$START"

CIRCOM_IMAGE="picus-with-circom"
GNARK_IMAGE="picus-with-gnark"

# Timeout: 10 min for the tool, extra 5 min grace for podman
T_HOURS=${T_HOURS:-0}
T_MINUTES=${T_MINUTES:-30}
T_SECONDS=${T_SECONDS:-0}
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)
PODMAN_TIMEOUT=$(( (T_HOURS * 3600) + ((T_MINUTES + 5) * 60) + T_SECONDS ))

BUILD=0
for arg in "$@"; do
    [[ "$arg" == "--build" ]] && BUILD=1
done

# ── Build images ────────────────────────────────────────────────────────────
if [[ $BUILD -eq 1 ]]; then
    echo "=== Building Circom image ==="
    bash "$CIRCUZZ_DIR/fyp_experiments/circom-picus/build_and_run_picus.sh" \
        HEAD "$CIRCOM_IMAGE" --no-run &
    CIRCOM_BUILD_PID=$!

    echo "=== Building Gnark image ==="
    bash "$CIRCUZZ_DIR/fyp_experiments/gnark-picus/build_and_run_picus.sh" \
        "$GNARK_IMAGE" --no-run &
    GNARK_BUILD_PID=$!

    wait $CIRCOM_BUILD_PID
    echo "Circom image ready."
    wait $GNARK_BUILD_PID
    echo "Gnark image ready."
fi

# ── Prepare output directories ───────────────────────────────────────────────
CIRCOM_OBJ="$CIRCUZZ_DIR/fyp_experiments/circom-picus/obj/$OBJ_DIR_SUFFIX"
GNARK_OBJ="$CIRCUZZ_DIR/fyp_experiments/gnark-picus/obj/$OBJ_DIR_SUFFIX"

CIRCOM_REPORT_HOST="$CIRCOM_OBJ/EXPERIMENT/explore/report"
GNARK_REPORT_HOST="$GNARK_OBJ/EXPERIMENT/explore/report"
CIRCOM_LOG="$CIRCOM_OBJ/EXPERIMENT/explore/logs/explore.log"
GNARK_LOG="$GNARK_OBJ/EXPERIMENT/explore/logs/explore.log"

mkdir -p "$CIRCOM_REPORT_HOST" "$(dirname "$CIRCOM_LOG")"
mkdir -p "$GNARK_REPORT_HOST" "$(dirname "$GNARK_LOG")"

TMP_DIR="/tmp/circuzz-picus-$START"
mkdir -p "$TMP_DIR"

# Paths inside the container (mounted at /app)
CIRCOM_REPORT_CONTAINER="/app/fyp_experiments/circom-picus/obj/$OBJ_DIR_SUFFIX/EXPERIMENT/explore/report"
GNARK_REPORT_CONTAINER="/app/fyp_experiments/gnark-picus/obj/$OBJ_DIR_SUFFIX/EXPERIMENT/explore/report"

CIRCOM_CONFIG="fyp_experiments/circom-picus/configs/circom-sample.json"
GNARK_CONFIG="fyp_experiments/gnark-picus/configs/gnark-sample.json"

# ── Run experiments (parallel) ───────────────────────────────────────────────
echo "=== Starting Circom experiment (timeout: $TOOL_TIMEOUT) ==="
podman run \
    --timeout=$PODMAN_TIMEOUT \
    --pids-limit=-1 \
    --cpus=2 \
    -v "$CIRCUZZ_DIR:/app" \
    -v "$TMP_DIR:/tmp" \
    --rm \
    "$CIRCOM_IMAGE" \
    python3 cli.py explore \
        --tool circom \
        -v3 \
        --timeout "$TOOL_TIMEOUT" \
        --working-dir "/tmp/circom/explore/working" \
        --report-dir "$CIRCOM_REPORT_CONTAINER" \
        --seed "$SEED" \
        --config "$CIRCOM_CONFIG" \
    > "$CIRCOM_LOG" 2>&1 &
CIRCOM_PID=$!

echo "=== Starting Gnark experiment (timeout: $TOOL_TIMEOUT) ==="
podman run \
    --timeout=$PODMAN_TIMEOUT \
    --pids-limit=-1 \
    --cpus=2 \
    -v "$CIRCUZZ_DIR:/app" \
    -v "$TMP_DIR:/tmp" \
    --rm \
    -e GOCACHE=/tmp/go-cache \
    "$GNARK_IMAGE" \
    python3 cli.py explore \
        --tool gnark \
        -v3 \
        --timeout "$TOOL_TIMEOUT" \
        --working-dir "/tmp/gnark/explore/working" \
        --report-dir "$GNARK_REPORT_CONTAINER" \
        --seed "$SEED" \
        --config "$GNARK_CONFIG" \
    > "$GNARK_LOG" 2>&1 &
GNARK_PID=$!

# Kill both containers on Ctrl-C
trap 'echo "Interrupted — killing experiments..."; kill $CIRCOM_PID $GNARK_PID 2>/dev/null; rm -rf "$TMP_DIR"; exit 1' INT TERM

echo "Both experiments running. Waiting..."
wait $CIRCOM_PID && CIRCOM_RC=0 || CIRCOM_RC=$?
wait $GNARK_PID  && GNARK_RC=0  || GNARK_RC=$?

rm -rf "$TMP_DIR"

echo ""
echo "Circom exit code: $CIRCOM_RC  (log: $CIRCOM_LOG)"
echo "Gnark  exit code: $GNARK_RC   (log: $GNARK_LOG)"

# ── Produce report ───────────────────────────────────────────────────────────
CIRCOM_CSV="$CIRCOM_REPORT_HOST/summary.csv"
GNARK_CSV="$GNARK_REPORT_HOST/summary.csv"

REPORT_FILE="$EVAL_DIR/report-$START.txt"

{
    echo "Picus Constrainedness Report"
    echo "Generated: $(date)"
    echo "Seed: $SEED"
    echo "Duration: $TOOL_TIMEOUT"
    echo ""

    CSVS=()
    if [[ -f "$CIRCOM_CSV" ]]; then
        CSVS+=("$CIRCOM_CSV")
    else
        echo "WARNING: Circom summary.csv not found at $CIRCOM_CSV"
    fi
    if [[ -f "$GNARK_CSV" ]]; then
        CSVS+=("$GNARK_CSV")
    else
        echo "WARNING: Gnark summary.csv not found at $GNARK_CSV"
    fi

    if [[ ${#CSVS[@]} -gt 0 ]]; then
        python3 "$ANALYSE" "${CSVS[@]}"
    else
        echo "No CSV files found — cannot produce statistics."
    fi
} | tee "$REPORT_FILE"

echo ""
echo "Report saved to: $REPORT_FILE"
