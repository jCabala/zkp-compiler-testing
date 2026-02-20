#!/bin/bash
#
# This scripts runs the experiments
# It requires that the podman-build.sh script was run beforehand!
# The script must be started from the project's root directory
#

set -x
start=`date +%s`

# =================================================
#                  Configuration
# =================================================

# Going into the script directory
SCRIPT_DIR=$(dirname "$0")
CIRCUZZ_DIR=$(realpath "$SCRIPT_DIR/../..")

echo CIRCUZZ_DIR is $CIRCUZZ_DIR

NUM_CPUS=2

SEED=2003
VERBOSITY=3
REPS=10

TMP_DIR=/tmp/circuzz/seed-$SEED-date-$start
OBJ_DIR=obj/seed-$SEED-date-$start
WAIT_BETWEEN=2

# Timeout settings
T_SECONDS=0
T_MINUTES=0
T_HOURS=24

# Configs
CIRCOM_CONFIG="fyp_experiments/circom-picus/configs/circom.json"

# =================================================
#                 Implementation
# =================================================

# gives the tool extra 5m to shutdown, calculates everything into seconds
PODMAN_TIMEOUT=$((($T_HOURS * 60 * 60) + (($T_MINUTES + 5) * 60) + $T_SECONDS))
# uses the exact values given in hms format style
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)

# seed randomness
RANDOM=$SEED

# Change dir to script dir
cd $SCRIPT_DIR

# create folder structure
mkdir -p $OBJ_DIR

# setup tmp file
mkdir -p $TMP_DIR

# helper function
function start() {

    CONFIG=""
    # Setup config based on tool
    if [[ $1 == "circom" ]]; then
        CONFIG=$CIRCOM_CONFIG
    else
        echo "unknown tool $1"
        exit 1
    fi

    EXPLORE_REP_DIR=$OBJ_DIR/$4/explore/report
    LOG_DIR_RUN=$OBJ_DIR/$4/explore/logs
    EXPLORE_WORK_DIR=/tmp/$4/explore/working
    PREFIXED_EXPLORE_REP_DIR=/app/fyp_experiments/circom-picus/$OBJ_DIR/$4/explore/report

    mkdir -p "$EXPLORE_REP_DIR"
    mkdir -p "$LOG_DIR_RUN"

    podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=$NUM_CPUS -v $CIRCUZZ_DIR:/app -v $TMP_DIR:/tmp --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $PREFIXED_EXPLORE_REP_DIR --seed $4 --config $CONFIG > $LOG_DIR_RUN/$3-explore.log 2>&1
}


# get a random seed for experiments
R=$RANDOM
IDX=1

# Setup the image
IMAGE_NAME=picus-with-circom
echo "Building the image $IMAGE_NAME"
"${SCRIPT_DIR}/build_and_run_picus.sh" HEAD "$IMAGE_NAME" --no-run

echo "Starting experiments...."
start circom $IMAGE_NAME "EXPERIMENT" $R &
echo "started circom with picus"

# wait for all to finish
wait $(jobs -p)

# clean up temporary
rm -rf $TMP_DIR

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"