#!/bin/bash

#
# This scripts starts an exploration for all tools
# It requires that the podman-build.sh script was run beforehand!
# 

set -x
start=`date +%s`


SCRIPT_PATH=$(dirname "$(realpath "$0")")
CIRCUZZ_ROOT=$(realpath "$SCRIPT_PATH/../../")

# =================================================
#                  Configuration
# =================================================

# Configa paths must be relative to CIRCUZZ_ROOT
CIRCOM_CONFIG=fyp_experiments/fully-constraint-circom/config/circom.json

IMAGE_CIRCOM_DEFAULT="localhost/circom-latest:latest"

SEED=2131
VERBOSITY=3
USE_TMP=1

# Timeout settings
T_SECONDS=0
T_MINUTES=0
T_HOURS=24

CIRCOM_NUM=1
CIRCOM_CPUS=2

TMP_DIR=/tmp/circuzz/seed-$SEED-date-$start
OBJ_DIR=$SCRIPT_PATH/obj/seed-$SEED-date-$start
WAIT_BETWEEN=2

# ----------------------------- DO NOT TOUCH -----------------------------

# =================================================
#                 Implementation
# =================================================

# gives the tool extra 5m to shutdown, calculates everything into seconds
PODMAN_TIMEOUT=$((($T_HOURS * 60 * 60) + (($T_MINUTES + 5) * 60) + $T_SECONDS))
# uses the exact values given in hms format style
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)

# Get into the experiments directory
cd $SCRIPT_PATH

# seed randomness
RANDOM=$SEED

# create folder structure
mkdir -p $OBJ_DIR

# setup tmp file
if [[ $USE_TMP -eq 1 ]]; then
    mkdir -p $TMP_DIR
fi

# helper function (tool, image, unique-name, cpus, random)
function start() {
    CONFIG=""
    if [[ $1 == "circom" ]]; then
        CONFIG=$CIRCOM_CONFIG
    # elif [[ $1 == "corset" ]]; then
    #     CONFIG=$CORSET_CONFIG
    elif [[ $1 == "gnark" ]]; then
        CONFIG=$GNARK_CONFIG
    elif [[ $1 == "noir" ]]; then
        CONFIG=$NOIR_CONFIG
    else
        echo "unknown tool $1"
        exit 1
    fi

    echo "Starting $1 with seed $5 ..."

    EXPLORE_REP_DIR=$OBJ_DIR/$3/explore/report
    LOG_DIR_RUN=$OBJ_DIR/$3/explore/logs
    PREFIXED_EXPLORE_REP_DIR=/app/fyp_experiments/fully-constraint-circom/obj/seed-$SEED-date-$start/$3/explore/report
    if [[ $USE_TMP -eq 1 ]]; then
        # tmp folders are cleaned above
        EXPLORE_WORK_DIR=/tmp/$3/explore/working
    else
        EXPLORE_WORK_DIR=$OBJ_DIR/$3/explore/working
    fi

    mkdir -p "$EXPLORE_REP_DIR"
    mkdir -p "$LOG_DIR_RUN"

    # start explorer
    if [[ $USE_TMP -eq 1 ]]; then
<<<<<<< HEAD
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$4 --memory=4g -v $CIRCUZZ_ROOT/:/app -v $TMP_DIR:/tmp --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $5 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1
    else
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$4 --memory=4g -v $CIRCUZZ_ROOT/:/app --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $5 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1
=======
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$4 -v $CIRCUZZ_ROOT/:/app -v $TMP_DIR:/tmp --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $5 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1
    else
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$4 -v $CIRCUZZ_ROOT/:/app --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $5 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1
>>>>>>> 8829a07 (feat: Updated configs)
    fi
}

# circom
if [[ $CIRCOM_NUM -ne 0 ]]; then
    PIDS=()
    for i in $(seq 1 $CIRCOM_NUM);
    do
        R=$RANDOM
        start circom $IMAGE_CIRCOM_DEFAULT circom-$i $CIRCOM_CPUS $R &
        PIDS+=($!)
        echo "Started circom $i/$CIRCOM_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done

    wait "${PIDS[@]}"
fi

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"
