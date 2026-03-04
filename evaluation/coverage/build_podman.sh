#!/usr/bin/env bash
set -euo pipefail
set -x

SCRIPT_DIR=$(dirname "$(realpath "$0")")
REPO_ROOT=$(realpath "$SCRIPT_DIR/../..")
COVERAGE_ROOT="$SCRIPT_DIR"

IMAGE_CIRCOM_COVERAGE="${IMAGE_CIRCOM_COVERAGE:-localhost/smt-exp-circom-coverage:latest}"
IMAGE_CIRCUZZ_COVERAGE="${IMAGE_CIRCUZZ_COVERAGE:-localhost/circuzz-circom-coverage:latest}"

LOG_DIR="$COVERAGE_ROOT/obj/build_podman/logs"
mkdir -p "$LOG_DIR"

podman build \
  --logfile "$LOG_DIR/circom-coverage.log" \
  -t "$IMAGE_CIRCOM_COVERAGE" \
  -f "$SCRIPT_DIR/images/circom-smt-exp-coverage.docker" \
  "$REPO_ROOT"

podman build \
  --logfile "$LOG_DIR/circuzz-coverage.log" \
  -t "$IMAGE_CIRCUZZ_COVERAGE" \
  -f "$SCRIPT_DIR/images/circom-circuzz-coverage.docker" \
  "$REPO_ROOT"
