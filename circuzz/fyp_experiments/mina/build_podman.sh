#!/bin/bash
#
# This scripts builds all required containers for Mina/o1js
# The script must be started from the project's root directory
#
# NOTE: This script might run for some hours depending on
#       internet speed and processor power.
#
# NOTE: If a command fails it might be due to a lost connection
#       during a download. It is safe to start this script again. 

set -e -x
start=`date +%s`

# -----------------------------------------
# config and flags for building
# -----------------------------------------

IMAGE_BASE=circuzz/base
IMAGE_MINA_BASE=circuzz/mina-base

# build flags
BUILD_BASE=0
BUILD_MINA_BASE=0
BUILD_MINA=1

# -----------------------------------------
# Setup debug-log folder structure
# -----------------------------------------

mkdir -p ./obj/build_podman
mkdir -p ./obj/build_podman/logs
mkdir -p ./obj/build_podman/logs/build
rm -rf ./obj/build_podman/logs/build/*
LOG_FOLDER="./obj/build_podman/logs/build"


# Get into experiments directory
SCRIPT_PATH=$(dirname "$(realpath "$0")")
CIRCUZZ_ROOT=$(realpath "$SCRIPT_PATH/../..")

cd $SCRIPT_PATH

# -----------------------------------------
# base container
# -----------------------------------------

if [[ $BUILD_BASE -eq 1 ]]; then
    echo "Building base image ..."

    podman build --logfile="$LOG_FOLDER/base.log" -t $IMAGE_BASE -f $CIRCUZZ_ROOT/images/base.docker $CIRCUZZ_ROOT

    echo "Building base image done!"
else
    echo "Skipping base image build ..."
fi

# -----------------------------------------
# mina containers
# -----------------------------------------

if [[ $BUILD_MINA_BASE -eq 1 ]]; then
    echo "Building mina base image ..."

    podman build --logfile="$LOG_FOLDER/mina-base.log" -t $IMAGE_MINA_BASE -f $CIRCUZZ_ROOT/images/mina-base.docker $CIRCUZZ_ROOT

    echo "Building mina base image done!"
else
    echo "Skipping mina base image build ..."
fi

if [[ $BUILD_MINA -eq 1 ]]; then
    echo "Building latest mina image ..."

    podman build --logfile="$LOG_FOLDER/mina-latest.log" -t mina-latest -f $CIRCUZZ_ROOT/images/mina.docker --build-arg=O1JS_VERSION=HEAD $CIRCUZZ_ROOT &

    wait $(jobs -p) # <--- join
    echo "Building mina images done!"
else
    echo "Skipping mina image build ..."
fi

# -----------------------------------------
# Finallize 
# -----------------------------------------

# check for absense of successful tags in log files
error_logs="$(grep -L 'Successfully tagged localhost/circuzz\|Successfully tagged localhost/mina' $LOG_FOLDER/*)"
if [[ ! -z $error_logs ]]; then
    echo "Unable to build some dependencies! See following logs:"
    echo $error_logs
fi

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"
