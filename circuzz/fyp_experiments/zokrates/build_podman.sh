#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

IMAGE_NAME="circuzz-zokrates:latest"
DOCKERFILE="../../images/zokrates.docker"

echo "[+] Building ZoKrates image with Podman"
podman build \
  --pull=always \
  -f "${DOCKERFILE}" \
  -t "${IMAGE_NAME}" \
  .

echo "[+] Build finished"
echo "[+] Verifying ZoKrates installation"
podman run --rm "${IMAGE_NAME}" zokrates --version
podman run --rm "$IMAGE_NAME" python3 --version