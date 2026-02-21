#!/usr/bin/env bash
set -euo pipefail
set -x

SCRIPT_DIR=$(dirname "$(realpath "$0")")
REPO_ROOT=$(realpath "$SCRIPT_DIR/../..")

IMAGE_CIRCOM="${IMAGE_CIRCOM:-localhost/smt-exp-circom:latest}"
IMAGE_GNARK="${IMAGE_GNARK:-localhost/smt-exp-gnark:latest}"

BUILD_CIRCOM="${BUILD_CIRCOM:-1}"
BUILD_GNARK="${BUILD_GNARK:-1}"

LOG_DIR="$SCRIPT_DIR/obj/build_podman/logs"
mkdir -p "$LOG_DIR"

if [[ "$BUILD_CIRCOM" -eq 1 ]]; then
  podman build \
    --logfile "$LOG_DIR/circom.log" \
    -t "$IMAGE_CIRCOM" \
    -f "$SCRIPT_DIR/images/circom-smt-exp.docker" \
    "$REPO_ROOT"
fi

if [[ "$BUILD_GNARK" -eq 1 ]]; then
  podman build \
    --logfile "$LOG_DIR/gnark.log" \
    -t "$IMAGE_GNARK" \
    -f "$SCRIPT_DIR/images/gnark-smt-exp.docker" \
    "$REPO_ROOT"
fi
