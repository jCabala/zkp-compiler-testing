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
CIRCOM_CONFIG=fyp_experiments/quadratic-circuzz/config/circom.json
# CORSET_CONFIG=fyp_experiments/quadratic-circuzz/config/corset.json
GNARK_CONFIG=fyp_experiments/quadratic-circuzz/config/gnark.json
NOIR_CONFIG=fyp_experiments/quadratic-circuzz/config/noir.json

IMAGE_CIRCOM_DEFAULT="circom-latest"
# IMAGE_CORSET_DEFAULT="corset-latest"
IMAGE_GNARK_DEFAULT="gnark-latest"
IMAGE_NOIR_DEFAULT="noir-latest"

SEED=2003
VERBOSITY=3
USE_TMP=1

# Timeout settings
T_SECONDS=0
T_MINUTES=0
T_HOURS=24

CIRCOM_NUM=1
CIRCOM_CPUS=2
# CORSET_NUM=3
# CORSET_CPUS=1
GNARK_NUM=0
GNARK_CPUS=0
NOIR_NUM=0
NOIR_CPUS=0

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
    PREFIXED_EXPLORE_REP_DIR=/app/fyp_experiments/quadratic-circuzz/obj/seed-$SEED-date-$start/$3/explore/report
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
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$4 -v $CIRCUZZ_ROOT/:/app -v $TMP_DIR:/tmp --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $5 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1 &
    else
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$4 -v $CIRCUZZ_ROOT/:/app --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $5 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1 &
    fi

    wait $(jobs -p)
}

# circom
if [[ $CIRCOM_NUM -ne 0 ]]; then
    for i in $(seq 1 $CIRCOM_NUM);
    do
        R=$RANDOM
        start circom $IMAGE_CIRCOM_DEFAULT circom-$i $CIRCOM_CPUS $R &
        echo "Started circom $i/$CIRCOM_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# corset
# Corset cannot handle the quadratic generator yet, so we skip it
# if [[ $CORSET_NUM -ne 0 ]]; then
#     for i in $(seq 1 $CORSET_NUM);
#     do
#         R=$RANDOM
#         start corset $IMAGE_CORSET_DEFAULT corset-$i $CORSET_CPUS $R &
#         echo "Started corset $i/$CORSET_NUM with seed $R ..."
#         sleep $WAIT_BETWEEN
#     done
# fi

# gnark
if [[ $GNARK_NUM -ne 0 ]]; then
    for i in $(seq 1 $GNARK_NUM);
    do
        R=$RANDOM
        start gnark $IMAGE_GNARK_DEFAULT gnark-$i $GNARK_CPUS $R &
        echo "Started gnark $i/$GNARK_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# noir
if [[ $NOIR_NUM -ne 0 ]]; then
    for i in $(seq 1 $NOIR_NUM);
    do
        R=$RANDOM
        start noir $IMAGE_NOIR_DEFAULT noir-$i $NOIR_CPUS $R &
        echo "Started noir $i/$NOIR_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# wait for all to finish
wait $(jobs -p)

# clean up temporary
rm -rf $TMP_DIR

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"