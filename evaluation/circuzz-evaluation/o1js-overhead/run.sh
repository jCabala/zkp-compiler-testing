#!/usr/bin/env bash
#
# Run the o1js (Mina) throughput overhead experiment.
#
# Runs Circom and Gnark as baselines alongside the Mina (o1js) backend, then
# reports average time per test, tests per second, and relative throughput.
#
# Usage: ./run.sh [--build] [--no-mina]
#   --build    rebuild the Podman images before running (default: use existing)
#   --no-mina  skip the Mina backend (useful if mina-latest is not built yet)
#
# NOTE: The Mina image (mina-latest) must be built before running without
#       --no-mina. Build it with:
#           cd <circuzz-root>/fyp_experiments/mina && bash build_podman.sh
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

CIRCOM_IMAGE="circom-latest"
GNARK_IMAGE="gnark-latest"
MINA_IMAGE="mina-latest"

# Timeout: 30 min for the tool, extra 5 min grace for podman
T_HOURS=${T_HOURS:-0}
T_MINUTES=${T_MINUTES:-30}
T_SECONDS=${T_SECONDS:-0}
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)
PODMAN_TIMEOUT=$(( (T_HOURS * 3600) + ((T_MINUTES + 5) * 60) + T_SECONDS ))

BUILD=0
RUN_MINA=1
for arg in "$@"; do
    [[ "$arg" == "--build"   ]] && BUILD=1
    [[ "$arg" == "--no-mina" ]] && RUN_MINA=0
done

# ── Build images ──────────────────────────────────────────────────────────────
if [[ $BUILD -eq 1 ]]; then
    echo "=== Building Circom image ==="
    bash "$CIRCUZZ_DIR/fyp_experiments/fully-constraint-circom/build_podman.sh" &
    CIRCOM_BUILD_PID=$!

    echo "=== Building Gnark image ==="
    bash "$CIRCUZZ_DIR/fyp_experiments/quadratic-circuzz/build_podman.sh" &
    GNARK_BUILD_PID=$!

    if [[ $RUN_MINA -eq 1 ]]; then
        echo "=== Building Mina image ==="
        (cd "$CIRCUZZ_DIR/fyp_experiments/mina" && bash build_podman.sh) &
        MINA_BUILD_PID=$!
    fi

    wait $CIRCOM_BUILD_PID && echo "Circom image ready."
    wait $GNARK_BUILD_PID  && echo "Gnark image ready."
    [[ $RUN_MINA -eq 1 ]] && wait $MINA_BUILD_PID && echo "Mina image ready."
fi

# ── Prepare output directories ────────────────────────────────────────────────
BASE_OBJ="$CIRCUZZ_DIR/fyp_experiments/o1js-overhead/obj/$OBJ_DIR_SUFFIX"

CIRCOM_REPORT_HOST="$BASE_OBJ/circom/explore/report"
GNARK_REPORT_HOST="$BASE_OBJ/gnark/explore/report"
MINA_REPORT_HOST="$BASE_OBJ/mina/explore/report"

mkdir -p "$CIRCOM_REPORT_HOST" "$(dirname "$BASE_OBJ/circom/explore/logs/x")"
mkdir -p "$GNARK_REPORT_HOST"  "$(dirname "$BASE_OBJ/gnark/explore/logs/x")"
[[ $RUN_MINA -eq 1 ]] && mkdir -p "$MINA_REPORT_HOST" "$(dirname "$BASE_OBJ/mina/explore/logs/x")"

TMP_DIR="/tmp/circuzz-o1js-overhead-$START"
mkdir -p "$TMP_DIR"

# Container-side report paths (source mounted at /app)
CIRCOM_REPORT_CTR="/app/fyp_experiments/o1js-overhead/obj/$OBJ_DIR_SUFFIX/circom/explore/report"
GNARK_REPORT_CTR="/app/fyp_experiments/o1js-overhead/obj/$OBJ_DIR_SUFFIX/gnark/explore/report"
MINA_REPORT_CTR="/app/fyp_experiments/o1js-overhead/obj/$OBJ_DIR_SUFFIX/mina/explore/report"

CIRCOM_CONFIG="fyp_experiments/o1js-overhead/configs/circom.json"
GNARK_CONFIG="fyp_experiments/o1js-overhead/configs/gnark.json"
MINA_CONFIG="fyp_experiments/o1js-overhead/configs/mina.json"

CIRCOM_LOG="$BASE_OBJ/circom/explore/logs/explore.log"
GNARK_LOG="$BASE_OBJ/gnark/explore/logs/explore.log"
MINA_LOG="$BASE_OBJ/mina/explore/logs/explore.log"

# ── Run experiments (parallel) ────────────────────────────────────────────────
PIDS=()

echo "=== Starting Circom baseline (timeout: $TOOL_TIMEOUT) ==="
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
        --report-dir "$CIRCOM_REPORT_CTR" \
        --seed "$SEED" \
        --config "$CIRCOM_CONFIG" \
    > "$CIRCOM_LOG" 2>&1 &
PIDS+=($!)

echo "=== Starting Gnark baseline (timeout: $TOOL_TIMEOUT) ==="
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
        --report-dir "$GNARK_REPORT_CTR" \
        --seed "$SEED" \
        --config "$GNARK_CONFIG" \
    > "$GNARK_LOG" 2>&1 &
PIDS+=($!)

if [[ $RUN_MINA -eq 1 ]]; then
    echo "=== Starting Mina (o1js) backend (timeout: $TOOL_TIMEOUT) ==="
    podman run \
        --timeout=$PODMAN_TIMEOUT \
        --pids-limit=-1 \
        --cpus=4 \
        -m 32g \
        -v "$CIRCUZZ_DIR:/app" \
        -v "$TMP_DIR:/tmp" \
        --rm \
        "$MINA_IMAGE" \
        python3 cli.py explore \
            --tool mina \
            -v3 \
            --timeout "$TOOL_TIMEOUT" \
            --working-dir "/tmp/mina/explore/working" \
            --report-dir "$MINA_REPORT_CTR" \
            --seed "$SEED" \
            --config "$MINA_CONFIG" \
        > "$MINA_LOG" 2>&1 &
    PIDS+=($!)
fi

trap 'echo "Interrupted — killing experiments..."; kill "${PIDS[@]}" 2>/dev/null; rm -rf "$TMP_DIR"; exit 1' INT TERM

echo "All experiments running. Waiting..."
for pid in "${PIDS[@]}"; do
    wait "$pid" || true
done

rm -rf "$TMP_DIR"

echo ""
echo "Circom exit code recorded in: $CIRCOM_LOG"
echo "Gnark  exit code recorded in: $GNARK_LOG"
[[ $RUN_MINA -eq 1 ]] && echo "Mina   exit code recorded in: $MINA_LOG"

# ── Produce report ────────────────────────────────────────────────────────────
CIRCOM_CSV="$CIRCOM_REPORT_HOST/summary.csv"
GNARK_CSV="$GNARK_REPORT_HOST/summary.csv"
MINA_CSV="$MINA_REPORT_HOST/summary.csv"

REPORT_FILE="$EVAL_DIR/report-$START.txt"

{
    echo "o1js Throughput Overhead Report"
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
    if [[ $RUN_MINA -eq 1 ]]; then
        if [[ -f "$MINA_CSV" ]]; then
            CSVS+=("$MINA_CSV")
        else
            echo "WARNING: Mina summary.csv not found at $MINA_CSV"
        fi
    fi

    if [[ ${#CSVS[@]} -gt 0 ]]; then
        python3 "$ANALYSE" "${CSVS[@]}"
    else
        echo "No CSV files found — cannot produce statistics."
    fi
} | tee "$REPORT_FILE"

echo ""
echo "Report saved to: $REPORT_FILE"
