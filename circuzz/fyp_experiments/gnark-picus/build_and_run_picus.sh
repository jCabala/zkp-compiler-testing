#!/usr/bin/env bash
set -euo pipefail

# build_and_run_picus.sh
# Usage: ./build_and_run_picus.sh [IMAGE_NAME]
# Example: ./build_and_run_picus.sh picus-with-gnark

IMAGE_NAME="${1:-picus-with-gnark}"

# directory containing this script (build context)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE_PATH="$SCRIPT_DIR/Dockerfile"

echo "Building image '$IMAGE_NAME' from '$DOCKERFILE_PATH'"
podman build \
  --format docker \
  --tag "${IMAGE_NAME}" \
  -f "${DOCKERFILE_PATH}" \
  "${SCRIPT_DIR}"

echo "Build finished. Running container from image '${IMAGE_NAME}'."
# Run an interactive shell in the built image

# Don't run if the flag --no-run is provided
if [[ "${2:-}" == "--no-run" ]]; then
    echo "Skipping container run as per --no-run flag."
    exit 0
fi

podman run -it "${IMAGE_NAME}" bash
