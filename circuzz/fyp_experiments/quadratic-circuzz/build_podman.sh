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
IMAGE_CORSET_BASE=circuzz/corset-base
IMAGE_GNARK_BASE=circuzz/gnark-base
IMAGE_NOIR_TOOLCHAIN_BASE=circuzz/noir-toolchain-base
IMAGE_NOIR_BASE=circuzz/noir-base

# build flags
BUILD_BASE=0

BUILD_CIRCOM_BASE=0
BUILD_CIRCOM=1

BUILD_CORSET_BASE=0
BUILD_CORSET=0

BUILD_GNARK_BASE=0
BUILD_GNARK=0

BUILD_NOIR_TOOLCHAIN_BASE=0
BUILD_NOIR_BASE=0
BUILD_NOIR=0

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

# -----------------------------------------
# corset containers
# -----------------------------------------

if [[ $BUILD_CORSET_BASE -eq 1 ]]; then
    echo "Building base corset image ..."

    podman build --logfile="$LOG_FOLDER/corset-base.log" -t $IMAGE_CORSET_BASE -f $CIRCUZZ_ROOT/images/corset-base.docker $CIRCUZZ_ROOT

    echo "Building base corset image done!"
else
    echo "Skipping corset base image build ..."
fi

if [[ $BUILD_CORSET -eq 1 ]]; then
    echo "Building latest corset image ..."

    podman build --logfile="$LOG_FOLDER/corset-latest.log" -t corset-latest -f $CIRCUZZ_ROOT/images/corset.docker --build-arg=CORSET_COMMIT=HEAD $CIRCUZZ_ROOT &

    wait $(jobs -p) # <--- join
    echo "Building corset images done!"
else
    echo "Skipping corset image build ..."
fi

# -----------------------------------------
# gnark containers
# -----------------------------------------

if [[ $BUILD_GNARK_BASE -eq 1 ]]; then
    echo "Building gnark base image ..."

    podman build --logfile="$LOG_FOLDER/gnark-base.log" -t $IMAGE_GNARK_BASE -f $CIRCUZZ_ROOT/images/gnark-base.docker $CIRCUZZ_ROOT

    echo "Building gnark base image done!"
else
    echo "Skipping gnark base image build ..."
fi

if [[ $BUILD_GNARK -eq 1 ]]; then
    echo "Building latest gnark image ..."

    podman build --logfile="$LOG_FOLDER/gnark-latest.log" -t gnark-latest -f $CIRCUZZ_ROOT/images/gnark.docker --build-arg=GNARK_COMMIT=HEAD $CIRCUZZ_ROOT

    wait $(jobs -p) # <--- join
    echo "Building gnark images done!"
else
    echo "Skipping gnark image build ..."
fi

# -----------------------------------------
# noir containers
# -----------------------------------------
#
#
# NOTE: due to noirs download of bb, it is best to not execute it in parallel

if [[ $BUILD_NOIR_BASE -eq 1 ]]; then
    echo "Building noir toolchain base image ..."

    podman build --logfile="$LOG_FOLDER/noir-toolchain-base.log" -t $IMAGE_NOIR_TOOLCHAIN_BASE -f $CIRCUZZ_ROOT/images/noir-toolchain-base.docker --build-arg=RUST_VERSION=$RUST_VERSION --build-arg=GO_VERSION=$GO_VERSION $CIRCUZZ_ROOT

    echo "Building noir toolchain base image done!"

    echo "Building noir base image ..."

    podman build --logfile="$LOG_FOLDER/noir-base.log" -t $IMAGE_NOIR_BASE -f $CIRCUZZ_ROOT/images/noir-base.docker $CIRCUZZ_ROOT

    echo "Building noir base image done!"
else
    echo "Skipping noir base image build ..."
fi

if [[ $BUILD_NOIR -eq 1 ]]; then
    echo "Building noir images ..."

    podman build --logfile="$LOG_FOLDER/noir-latest.log" -t noir-latest -f $CIRCUZZ_ROOT/images/noir.docker --build-arg=NOIR_COMMIT=HEAD --build-arg=BB_VERSION=0.56.0 $CIRCUZZ_ROOT &

    wait $(jobs -p) # <--- join
    echo "Building noir images done!"
else
    echo "Skipping noir image build ..."
fi

# -----------------------------------------
# Finallize 
# -----------------------------------------

# check for absense of successful tags in log files
error_logs="$(grep -L 'Successfully tagged localhost/circuzz' $LOG_FOLDER/*)"
if [[ ! -z $error_logs ]]; then
    echo "Unable to build some dependencies! See following logs:"
    echo $error_logs
fi

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"
