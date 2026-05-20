#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

clone_or_skip() {
    local url="$1"
    local dir="$2"
    if [ -d "$dir/.git" ]; then
        echo "Already cloned: $dir — skipping"
    else
        echo "Cloning $url -> $dir"
        git clone "$url" "$dir"
    fi
}

clone_or_skip "https://github.com/noir-lang/noir"       "noir"
clone_or_skip "https://github.com/iden3/circom"         "circom"
clone_or_skip "https://github.com/ConsenSys/gnark"      "gnark"
clone_or_skip "https://github.com/Zokrates/ZoKrates"    "zokrates"

echo "Done."
