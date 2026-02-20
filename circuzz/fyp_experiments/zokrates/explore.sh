#!/bin/bash

#
# This script starts an exploration for the ZoKrates backend.
# Assumes you want to use /tmp for working directories (always).
# It requires that the podman-build.sh script was run beforehand!
#

set -x
start=$(date +%s)

SCRIPT_PATH=$(dirname "$(realpath "$0")")
CIRCUZZ_ROOT=$(realpath "$SCRIPT_PATH/../../")

# =================================================
#                  Configuration
# =================================================

# Config paths must be relative to CIRCUZZ_ROOT
ZOKRATES_ARITHMETIC_CONFIG=fyp_experiments/zokrates/config/zokrates-arithmetic.json
ZOKRATES_BOOLEAN_CONFIG=fyp_experiments/zokrates/config/zokrates-boolean.json

IMAGE_ZOKRATES_DEFAULT="circuzz-zokrates"

SEED=11132
VERBOSITY=3

# Timeout settings
T_SECONDS=0
T_MINUTES=0
T_HOURS=24

ZOKRATES_ARITHMETIC_NUM=1
ZOKRATES_ARITHMETIC_CPUS=4
ZOKRATES_BOOLEAN_NUM=0
ZOKRATES_BOOLEAN_CPUS=0

MEM_LIMIT=4g

TMP_DIR=/tmp/circuzz/seed-$SEED-date-$start
OBJ_DIR=$SCRIPT_PATH/obj/seed-$SEED-date-$start
WAIT_BETWEEN=2

# ----------------------------- DO NOT TOUCH -----------------------------

# =================================================
#                 Implementation
# =================================================

cleanup() {
    rm -rf "$TMP_DIR"
    end=$(date +%s)
    runtime=$((end - start))
    echo "Time taken for exploration: $runtime s" >> "$OBJ_DIR/explore_time.txt"
    echo "finished in $runtime s"
}

trap cleanup EXIT INT TERM

# gives the tool extra 5m to shutdown, calculates everything into seconds
PODMAN_TIMEOUT=$(( (T_HOURS * 60 * 60) + ((T_MINUTES + 5) * 60) + T_SECONDS ))
# uses the exact values given in hms format style
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)

# Get into the experiments directory
cd "$SCRIPT_PATH" || exit 1

# seed randomness
RANDOM=$SEED

# create folder structure
mkdir -p "$OBJ_DIR"
mkdir -p "$TMP_DIR"

store_config() {
    touch "$OBJ_DIR/explore_config.txt"
    {
        echo "ZOKRATES_ARITHMETIC_CONFIG=$ZOKRATES_ARITHMETIC_CONFIG"
        echo "ZOKRATES_BOOLEAN_CONFIG=$ZOKRATES_BOOLEAN_CONFIG"
        echo "IMAGE_ZOKRATES_DEFAULT=$IMAGE_ZOKRATES_DEFAULT"
        echo "SEED=$SEED"
        echo "VERBOSITY=$VERBOSITY"
        echo "T_HOURS=$T_HOURS"
        echo "T_MINUTES=$T_MINUTES"
        echo "T_SECONDS=$T_SECONDS"
        echo "ZOKRATES_ARITHMETIC_NUM=$ZOKRATES_ARITHMETIC_NUM"
        echo "ZOKRATES_ARITHMETIC_CPUS=$ZOKRATES_ARITHMETIC_CPUS"
        echo "ZOKRATES_BOOLEAN_NUM=$ZOKRATES_BOOLEAN_NUM"
        echo "ZOKRATES_BOOLEAN_CPUS=$ZOKRATES_BOOLEAN_CPUS"
    } >> "$OBJ_DIR/explore_config.txt"
}

# helper function (tool, image, unique-name, cpus, random, config)
start_one() {
    TOOL=$1
    IMAGE=$2
    NAME=$3
    CPUS=$4
    RSEED=$5
    CONFIG=$6

    echo "Starting $TOOL with seed $RSEED using config $CONFIG ..."

    EXPLORE_REP_DIR="$OBJ_DIR/$NAME/explore/report"
    LOG_DIR_RUN="$OBJ_DIR/$NAME/explore/logs"

    # IMPORTANT: report-dir must be inside /app (mounted CIRCUZZ_ROOT)
    PREFIXED_EXPLORE_REP_DIR="/app/fyp_experiments/zokrates/obj/seed-$SEED-date-$start/$NAME/explore/report"

    # Always use tmp
    EXPLORE_WORK_DIR="/tmp/$NAME/explore/working"

    # Store config in obj dir
    store_config

    mkdir -p "$EXPLORE_REP_DIR"
    mkdir -p "$LOG_DIR_RUN"

    podman run \
        --timeout="$PODMAN_TIMEOUT" \
        --pids-limit=-1 \
        --cpus="$CPUS" \
        -m "$MEM_LIMIT" \
        -v "$CIRCUZZ_ROOT/:/app:Z" \
        -v "$TMP_DIR:/tmp:Z" \
        -w /app \
        --rm \
        "$IMAGE" \
        python3 cli.py explore \
            --tool "$TOOL" \
            -v"$VERBOSITY" \
            --timeout "$TOOL_TIMEOUT" \
            --working-dir "$EXPLORE_WORK_DIR" \
            --report-dir "$PREFIXED_EXPLORE_REP_DIR" \
            --seed "$RSEED" \
            --config "$CONFIG" \
        > "$LOG_DIR_RUN/$NAME-explore.log" 2>&1 &
}

# zokrates arithmetic
if [[ $ZOKRATES_ARITHMETIC_NUM -ne 0 ]]; then
    for i in $(seq 1 $ZOKRATES_ARITHMETIC_NUM); do
        R=$RANDOM
        start_one zokrates "$IMAGE_ZOKRATES_DEFAULT" "zokrates-arithmetic-$i" "$ZOKRATES_ARITHMETIC_CPUS" "$R" "$ZOKRATES_ARITHMETIC_CONFIG"
        echo "Started zokrates-arithmetic $i/$ZOKRATES_ARITHMETIC_NUM with seed $R ..."
        sleep "$WAIT_BETWEEN"
    done
fi

# zokrates boolean
if [[ $ZOKRATES_BOOLEAN_NUM -ne 0 ]]; then
    for i in $(seq 1 $ZOKRATES_BOOLEAN_NUM); do
        R=$RANDOM
        start_one zokrates "$IMAGE_ZOKRATES_DEFAULT" "zokrates-boolean-$i" "$ZOKRATES_BOOLEAN_CPUS" "$R" "$ZOKRATES_BOOLEAN_CONFIG"
        echo "Started zokrates-boolean $i/$ZOKRATES_BOOLEAN_NUM with seed $R ..."
        sleep "$WAIT_BETWEEN"
    done
fi

# wait for all to finish
wait $(jobs -p)
