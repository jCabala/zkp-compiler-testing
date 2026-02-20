#!/bin/bash
#
# Builds Podman images used by SMT-fusion experiment.
# The script should be run from the experiment directory.
#

set -euo pipefail
set -x
start=$(date +%s)

SCRIPT_PATH=$(dirname "$(realpath "$0")")
CIRCUZZ_ROOT=$(realpath "$SCRIPT_PATH/../..")

mkdir -p "$SCRIPT_PATH/obj/build_podman/logs/build"
rm -rf "$SCRIPT_PATH/obj/build_podman/logs/build/"*
LOG_FOLDER="$SCRIPT_PATH/obj/build_podman/logs/build"

GO_VERSION="${GO_VERSION:-1.23.2}"
RUST_VERSION="${RUST_VERSION:-1.83.0}"

IMAGE_BASE="${IMAGE_BASE:-circuzz/base}"
IMAGE_CIRCOM_BASE="${IMAGE_CIRCOM_BASE:-circuzz/circom-base}"
IMAGE_GNARK_BASE="${IMAGE_GNARK_BASE:-circuzz/gnark-base}"
IMAGE_NOIR_TOOLCHAIN_BASE="${IMAGE_NOIR_TOOLCHAIN_BASE:-circuzz/noir-toolchain-base}"
IMAGE_NOIR_BASE="${IMAGE_NOIR_BASE:-circuzz/noir-base}"

IMAGE_CIRCOM="${IMAGE_CIRCOM:-circom-latest}"
IMAGE_GNARK="${IMAGE_GNARK:-gnark-latest}"
IMAGE_NOIR="${IMAGE_NOIR:-noir-latest}"
IMAGE_NOIR_PATCHED="${IMAGE_NOIR_PATCHED:-localhost/noir-latest-patched:latest}"
NOIR_BB_VERSION="${NOIR_BB_VERSION:-4.0.0-nightly.20260120}"

BUILD_BASE="${BUILD_BASE:-1}"
BUILD_CIRCOM_BASE="${BUILD_CIRCOM_BASE:-1}"
BUILD_GNARK_BASE="${BUILD_GNARK_BASE:-1}"
BUILD_NOIR_TOOLCHAIN_BASE="${BUILD_NOIR_TOOLCHAIN_BASE:-1}"
BUILD_NOIR_BASE="${BUILD_NOIR_BASE:-1}"
BUILD_CIRCOM="${BUILD_CIRCOM:-1}"
BUILD_GNARK="${BUILD_GNARK:-1}"
BUILD_NOIR="${BUILD_NOIR:-1}"
BUILD_NOIR_PATCHED="${BUILD_NOIR_PATCHED:-1}"

# WSL-safe mode: lower resource spikes during image builds.
SAFE_WSL="${SAFE_WSL:-0}"
if [[ "$SAFE_WSL" -eq 1 ]]; then
  BUILD_MEMORY="${BUILD_MEMORY:-4g}"
  BUILD_CPUS="${BUILD_CPUS:-2}"
  BUILD_JOBS="${BUILD_JOBS:-1}"
fi

BUILD_MEMORY="${BUILD_MEMORY:-}"
BUILD_CPUS="${BUILD_CPUS:-}"
BUILD_JOBS="${BUILD_JOBS:-}"

PODMAN_BUILD_FLAGS=()
if [[ -n "$BUILD_MEMORY" ]]; then
  PODMAN_BUILD_FLAGS+=(--memory "$BUILD_MEMORY")
fi
if [[ -n "$BUILD_CPUS" ]]; then
  # Podman build may not support --cpus on older versions.
  # Use CPU quota/period for wider compatibility.
  cpu_quota=$(awk "BEGIN { printf \"%d\", $BUILD_CPUS * 100000 }")
  PODMAN_BUILD_FLAGS+=(--cpu-period 100000 --cpu-quota "$cpu_quota")
fi
if [[ -n "$BUILD_JOBS" ]]; then
  PODMAN_BUILD_FLAGS+=(--jobs "$BUILD_JOBS")
fi

podman_build() {
  podman build "${PODMAN_BUILD_FLAGS[@]}" "$@"
}

cd "$SCRIPT_PATH"

if [[ $BUILD_BASE -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/base.log" -t "$IMAGE_BASE" \
    -f "$CIRCUZZ_ROOT/images/base.docker" \
    --build-arg=RUST_VERSION="$RUST_VERSION" \
    --build-arg=GO_VERSION="$GO_VERSION" \
    "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_CIRCOM_BASE -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/circom-base.log" -t "$IMAGE_CIRCOM_BASE" \
    -f "$CIRCUZZ_ROOT/images/circom-base.docker" "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_GNARK_BASE -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/gnark-base.log" -t "$IMAGE_GNARK_BASE" \
    -f "$CIRCUZZ_ROOT/images/gnark-base.docker" "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_NOIR_TOOLCHAIN_BASE -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/noir-toolchain-base.log" -t "$IMAGE_NOIR_TOOLCHAIN_BASE" \
    -f "$CIRCUZZ_ROOT/images/noir-toolchain-base.docker" \
    --build-arg=RUST_VERSION="$RUST_VERSION" \
    --build-arg=GO_VERSION="$GO_VERSION" \
    "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_NOIR_BASE -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/noir-base.log" -t "$IMAGE_NOIR_BASE" \
    -f "$CIRCUZZ_ROOT/images/noir-base.docker" "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_CIRCOM -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/circom-latest.log" -t "$IMAGE_CIRCOM" \
    -f "$CIRCUZZ_ROOT/images/circom.docker" --build-arg=CIRCOM_COMMIT=HEAD "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_GNARK -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/gnark-latest.log" -t "$IMAGE_GNARK" \
    -f "$CIRCUZZ_ROOT/images/gnark.docker" --build-arg=GNARK_COMMIT=HEAD "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_NOIR -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/noir-latest.log" -t "$IMAGE_NOIR" \
    -f "$CIRCUZZ_ROOT/images/noir.docker" --build-arg=NOIR_COMMIT=HEAD --build-arg=BB_VERSION="$NOIR_BB_VERSION" "$CIRCUZZ_ROOT"
fi

if [[ $BUILD_NOIR_PATCHED -eq 1 ]]; then
  podman_build --logfile="$LOG_FOLDER/noir-latest-patched.log" -t "$IMAGE_NOIR_PATCHED" \
    -f "$SCRIPT_PATH/images/noir-python-hotfix.docker" "$SCRIPT_PATH"
fi

end=$(date +%s)
runtime=$((end - start))
echo "finished in $runtime s"
