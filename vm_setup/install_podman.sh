#!/bin/bash
set -e

REPO_URL="https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_20.04"

echo "deb ${REPO_URL}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list

curl -L "${REPO_URL}/Release.key" | sudo apt-key add -

sudo apt-get update && sudo apt-get install -y podman

echo "Done! Podman version:"
podman --version

# Configure subuid/subgid ranges for the current user (required for rootless Podman).
# Without this, builds fail with "potentially insufficient UIDs or GIDs available in
# user namespace" when pulling images that have files owned by non-root GIDs.
CURRENT_USER=$(whoami)
EXISTING_MAX=$(awk -F: 'BEGIN{m=100000} {if($2+$3>m) m=$2+$3} END{print m}' /etc/subuid 2>/dev/null || echo 100000)
START=$EXISTING_MAX
END=$((START + 65535))
sudo usermod --add-subuids ${START}-${END} --add-subgids ${START}-${END} "$CURRENT_USER"
podman system migrate
echo "Configured subuid/subgid range ${START}-${END} for $CURRENT_USER"
