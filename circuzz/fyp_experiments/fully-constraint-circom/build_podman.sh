#!/bin/bash
#
# This scripts builds all required containers
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

GO_VERSION="1.23.2"
RUST_VERSION="1.83.0"

IMAGE_BASE=circuzz/base
IMAGE_CIRCOM_BASE=circuzz/circom-base

# build flags
BUILD_BASE=0

BUILD_CIRCOM_BASE=0
BUILD_CIRCOM=1

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

    podman build --logfile="$LOG_FOLDER/base.log" -t $IMAGE_BASE -f $CIRCUZZ_ROOT/images/base.docker --build-arg=RUST_VERSION=$RUST_VERSION --build-arg=GO_VERSION=$GO_VERSION $CIRCUZZ_ROOT

    echo "Building base image done!"
else
    echo "Skipping base image build ..."
fi

# -----------------------------------------
# circom containers
# -----------------------------------------

if [[ $BUILD_CIRCOM_BASE -eq 1 ]]; then
    echo "Building circom base image ..."

    podman build --logfile="$LOG_FOLDER/circom-base.log" -t $IMAGE_CIRCOM_BASE -f $CIRCUZZ_ROOT/images/circom-base.docker $CIRCUZZ_ROOT

    echo "Building circom base image done!"
else
    echo "Skipping circom base image build ..."
fi

if [[ $BUILD_CIRCOM -eq 1 ]]; then
    echo "Building latest circom image ..."

    podman build --logfile="$LOG_FOLDER/circom-latest.log" -t circom-latest -f $CIRCUZZ_ROOT/images/circom.docker --build-arg=CIRCOM_COMMIT=HEAD $CIRCUZZ_ROOT &
    wait $(jobs -p) # <--- join
    echo "Building circom images done!"
else
    echo "Skipping circom image build ..."
fi
