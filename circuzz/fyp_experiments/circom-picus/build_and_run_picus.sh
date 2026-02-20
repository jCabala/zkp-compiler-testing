#!/usr/bin/env bash
set -euo pipefail

# build_and_run_picus.sh
# Usage: ./build_and_run_picus.sh [CIRCOM_COMMIT] [IMAGE_NAME]
# Example: ./build_and_run_picus.sh v0.0.39 pycus-with-circom

CIRCOM_COMMIT="${1:-HEAD}"
IMAGE_NAME="${2:-picus-test}"

# directory containing this script (build context)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE_PATH="$SCRIPT_DIR/Dockerfile"

echo "Building image '$IMAGE_NAME' from '$DOCKERFILE_PATH' with CIRCOM_COMMIT=$CIRCOM_COMMIT"
podman build \
  --format docker \
  --tag "${IMAGE_NAME}" \
  --build-arg CIRCOM_COMMIT="${CIRCOM_COMMIT}" \
  -f "${DOCKERFILE_PATH}" \
  "${SCRIPT_DIR}"

echo "Build finished. Running container from image '${IMAGE_NAME}'."
# Run an interactive shell in the built image

# Don't run if the flag --no-run is provided
if [[ "${3:-}" == "--no-run" ]]; then
    echo "Skipping container run as per --no-run flag."
    exit 0
fi

podman run -it "${IMAGE_NAME}" bash
