#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
COVERAGE_ROOT=$(realpath "$SCRIPT_DIR/..")
OBJ_DIR="$COVERAGE_ROOT/obj/test-suite"
source "$SCRIPT_DIR/../../../smt-solver/experiments/common.sh"

CONTAINER_MEMORY="${CONTAINER_MEMORY:-64g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"
IMAGE_CIRCOM_COVERAGE="localhost/smt-exp-circom-coverage:latest"

if [[ "${IN_PODMAN:-0}" != "1" ]]; then
  podman run --rm \
    --name "coverage-test-suite-$$" \
    -v "$REPO_ROOT":/workspace \
    --workdir /workspace/evaluation/coverage/test-suite \
    --memory "$CONTAINER_MEMORY" \
    --memory-swap "$CONTAINER_MEMORY_SWAP" \
    -e IN_PODMAN=1 \
    "$IMAGE_CIRCOM_COVERAGE" \
    bash -lc "./coverage.sh --in-container"
  exit $?
fi

if [[ "${1:-}" != "--in-container" ]]; then
  echo "container mode expects: --in-container" >&2
  exit 1
fi

echo "[preflight] circom=$(which circom)" >&2
echo "[preflight] image=${IMAGE_CIRCOM_COVERAGE}" >&2
echo "[preflight] LLVM_PROFILE_FILE=${LLVM_PROFILE_FILE:-<unset>}" >&2
echo "[preflight] profraw dir: /coverage/profraw" >&2

if [[ -z "${LLVM_PROFILE_FILE:-}" || ! -d /coverage/profraw ]]; then
  echo "ERROR: coverage environment is not initialized" >&2
  echo "Run this script from the host so it can launch $IMAGE_CIRCOM_COVERAGE" >&2
  exit 1
fi

rm -f /coverage/profraw/*.profraw
mkdir -p "$OBJ_DIR"

TEST_EXIT=0
INTERRUPTED=0

handle_signal() {
  INTERRUPTED=1
}
trap handle_signal INT TERM

echo "[coverage] Running Circom cargo test suite..." >&2
set +e
(
  cd /circuzz/circom
  cargo test --workspace --no-fail-fast
) | tee "$OBJ_DIR/cargo_test.out"
TEST_EXIT=${PIPESTATUS[0]}
set -e

if [[ "$INTERRUPTED" -eq 1 ]]; then
  echo "[coverage] Test run interrupted; generating report from collected data..." >&2
elif [[ "$TEST_EXIT" -ne 0 ]]; then
  echo "[coverage] cargo test exited with $TEST_EXIT; generating report from collected data..." >&2
fi

set +e
bash "$COVERAGE_ROOT/generate_report.sh" test-suite
REPORT_EXIT=$?
set -e

if [[ "$INTERRUPTED" -eq 1 ]]; then
  exit 130
fi

if [[ "$TEST_EXIT" -ne 0 ]]; then
  exit "$TEST_EXIT"
fi

exit "$REPORT_EXIT"
