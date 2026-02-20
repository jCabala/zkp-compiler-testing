#!/bin/bash
set -e

REPO_URL="https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_20.04"

echo "deb ${REPO_URL}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list

curl -L "${REPO_URL}/Release.key" | sudo apt-key add -

sudo apt-get update && sudo apt-get install -y podman

echo "Done! Podman version:"
podman --version
