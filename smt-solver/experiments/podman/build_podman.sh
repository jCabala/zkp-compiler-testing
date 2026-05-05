#!/usr/bin/env bash
set -euo pipefail
set -x

SCRIPT_DIR=$(dirname "$(realpath "$0")")
REPO_ROOT=$(realpath "$SCRIPT_DIR/../..")
IMAGES_DIR="$REPO_ROOT/experiments/images"

IMAGE_CIRCOM="${IMAGE_CIRCOM:-localhost/smt-exp-circom:latest}"
IMAGE_GNARK="${IMAGE_GNARK:-localhost/smt-exp-gnark:latest}"
IMAGE_NOIR="${IMAGE_NOIR:-localhost/smt-exp-noir:latest}"
IMAGE_ZOKRATES="${IMAGE_ZOKRATES:-localhost/smt-exp-zokrates:latest}"

BUILD_CIRCOM="${BUILD_CIRCOM:-1}"
BUILD_GNARK="${BUILD_GNARK:-1}"
BUILD_NOIR="${BUILD_NOIR:-1}"
BUILD_ZOKRATES="${BUILD_ZOKRATES:-1}"

LOG_DIR="$SCRIPT_DIR/obj/build_podman/logs"
mkdir -p "$LOG_DIR"

if [[ "$BUILD_CIRCOM" -eq 1 ]]; then
  podman build \
    --logfile "$LOG_DIR/circom.log" \
    -t "$IMAGE_CIRCOM" \
    -f "$IMAGES_DIR/circom-smt-exp.docker" \
    "$REPO_ROOT"
fi

if [[ "$BUILD_GNARK" -eq 1 ]]; then
  podman build \
    --logfile "$LOG_DIR/gnark.log" \
    -t "$IMAGE_GNARK" \
    -f "$IMAGES_DIR/gnark-smt-exp.docker" \
    "$REPO_ROOT"
fi

if [[ "$BUILD_NOIR" -eq 1 ]]; then
  podman build \
    --logfile "$LOG_DIR/noir.log" \
    -t "$IMAGE_NOIR" \
    -f "$IMAGES_DIR/noir-smt-exp.docker" \
    "$REPO_ROOT"
fi

if [[ "$BUILD_ZOKRATES" -eq 1 ]]; then
  podman build \
    --logfile "$LOG_DIR/zokrates.log" \
    -t "$IMAGE_ZOKRATES" \
    -f "$IMAGES_DIR/zokrates-smt-exp.docker" \
    "$REPO_ROOT"
fi
