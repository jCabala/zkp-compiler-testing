#!/usr/bin/env bash
#
# Master runner for all Circuzz evaluation sub-experiments.
#
# Each sub-experiment runs sequentially with the same timeout.
#
# Usage:
#   ./run.sh [--build] [sub-experiment ...]
#
#   --build            rebuild Podman images before running
#   sub-experiment     run only the named experiment(s); if omitted, all run
#                      choices: picus-constrainedness  weak-sat  o1js-overhead
#
# Timeout (applies to all experiments):
#   T_HOURS   (default 0)
#   T_MINUTES (default 20)
#   T_SECONDS (default 0)
#
# Example — run everything for 1 hour:
#   T_HOURS=1 T_MINUTES=0 ./run.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse arguments ───────────────────────────────────────────────────────────
BUILD_FLAG=""
SELECTED=()
for arg in "$@"; do
    case "$arg" in
        --build) BUILD_FLAG="--build" ;;
        picus-constrainedness|weak-sat|o1js-overhead) SELECTED+=("$arg") ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

if [[ ${#SELECTED[@]} -eq 0 ]]; then
    SELECTED=(picus-constrainedness weak-sat o1js-overhead)
fi

# ── Timeout (shared across all experiments) ───────────────────────────────────
T_HOURS=${T_HOURS:-0}
T_MINUTES=${T_MINUTES:-30}
T_SECONDS=${T_SECONDS:-0}

export T_HOURS T_MINUTES T_SECONDS

# ── Run selected experiments concurrently ────────────────────────────────────
OVERALL_START=$(date +%s)
PIDS=()

for exp in "${SELECTED[@]}"; do
    echo "  Spawning: $exp  (timeout: ${T_HOURS}h${T_MINUTES}m${T_SECONDS}s)"
    bash "$SCRIPT_DIR/$exp/run.sh" $BUILD_FLAG &
    PIDS+=($!)
done

trap 'echo "Interrupted — killing all experiments..."; kill "${PIDS[@]}" 2>/dev/null; exit 1' INT TERM

for pid in "${PIDS[@]}"; do
    wait "$pid"
done

OVERALL_END=$(date +%s)
echo ""
echo "════════════════════════════════════════════════════════"
echo "  All experiments done in $(( OVERALL_END - OVERALL_START ))s"
echo "════════════════════════════════════════════════════════"
