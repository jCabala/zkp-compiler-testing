#!/usr/bin/env bash
#
# Artificial-bugs evaluation — run one tool at a time.
#
# Usage:
#   ./run.sh <tool>
#
# Tools:
#   smt-bool         -- yinyang on Bool benchmarks (sat + unsat + picus in parallel)
#   smt-ff           -- yinyang on FF   benchmarks (sat + unsat + picus in parallel)
#   circuzz-picus    -- circuzz fully-constrained, Picus oracle
#   circuzz-standard -- circuzz fully-constrained, standard metamorphic oracle
#
# Prerequisites:
#   - Build the artificial-bugs binary once:
#       cd <repo>/smt-solver/third_party/artificial-bugs/circom
#       cargo build --release
#   - IMAGE_CIRCOM  smt-exp-circom image  (default: localhost/smt-exp-circom:latest)
#   - IMAGE_CIRCUZZ circom-latest image   (default: circom-latest)
#
# Override circuzz timeout: T_HOURS=2 ./run.sh circuzz-picus

set -euo pipefail

TOOL="${1:-}"
if [[ -z "$TOOL" ]]; then
    echo "Usage: $0 <smt-bool|smt-ff|circuzz-picus|circuzz-standard>"
    exit 1
fi

case "$TOOL" in
    smt-bool|smt-ff|circuzz-picus|circuzz-standard) ;;
    *)
        echo "Unknown tool '$TOOL'. Choose: smt-bool | smt-ff | circuzz-picus | circuzz-standard"
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "$SCRIPT_DIR/../..")"
SMT_ROOT="$REPO_ROOT/smt-solver"
CIRCUZZ_ROOT="$REPO_ROOT/circuzz"

ARTBUGS_BIN="$SMT_ROOT/third_party/artificial-bugs/circom/target/release/circom"
ARTBUGS_CONFIG="$SCRIPT_DIR/configs/artbugs.json"

IMAGE_CIRCOM="${IMAGE_CIRCOM:-localhost/smt-exp-circom:latest}"
IMAGE_CIRCUZZ="${IMAGE_CIRCUZZ:-circom-latest}"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-16g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"

T_HOURS="${T_HOURS:-1}"
T_MINUTES="${T_MINUTES:-0}"
TOOL_TIMEOUT="$(printf "%sh%sm0s" "$T_HOURS" "$T_MINUTES")"
PODMAN_TIMEOUT=$(( (T_HOURS * 3600) + ((T_MINUTES + 5) * 60) ))

# ── Preflight ─────────────────────────────────────────────────────────────────

if [[ ! -x "$ARTBUGS_BIN" ]]; then
    echo "[error] artificial-bugs binary not found at: $ARTBUGS_BIN"
    echo "Build: cd $SMT_ROOT/third_party/artificial-bugs/circom && cargo build --release"
    exit 1
fi
if ! "$ARTBUGS_BIN" --help 2>&1 | grep -q "artificial-bugs-build"; then
    echo "[error] binary at $ARTBUGS_BIN is missing the 'artificial-bugs-build' marker"
    exit 1
fi

# ── Output directory ──────────────────────────────────────────────────────────

START=$(date +%s)
OBJ_DIR="$SCRIPT_DIR/obj/run-${START}-${TOOL}"
mkdir -p "$OBJ_DIR"
echo "$TOOL" > "$OBJ_DIR/tool.txt"

echo "[preflight] tool:   $TOOL"
echo "[preflight] binary: $ARTBUGS_BIN"
echo "[preflight] output: $OBJ_DIR"
echo ""

# ── SMT runner ────────────────────────────────────────────────────────────────

run_smt() {
    echo "Run the dedicated experiemnt in smt-solver/experiments/ with the given config name (e.g. smt_bool or smt_ff)."
}

# ── Circuzz runner ────────────────────────────────────────────────────────────
# Fix: mount the PARENT dir (not the report dir itself) so circuzz can freely
# rmtree/create the 'report' subdirectory without hitting a bind-mount EBUSY error.

run_circuzz() {
    local config_rel="$1"    # relative path inside /app
    local variant="$2"       # picus or standard

    # circuzz will create/manage $parent/report itself
    local parent="$OBJ_DIR/circuzz"
    mkdir -p "$parent"

    local container_parent="/output_parent"
    local container_report="$container_parent/report"
    local log="$OBJ_DIR/run.log"

    echo "=== Running circuzz-$variant (timeout: $TOOL_TIMEOUT) ==="
    podman run \
        --timeout="$PODMAN_TIMEOUT" \
        --pids-limit=-1 \
        --rm \
        --name "artbugs-circuzz-${variant}-$$" \
        -v "$CIRCUZZ_ROOT:/app" \
        -v "$ARTBUGS_BIN:/root/.cargo/bin/circom:ro" \
        -v "$ARTBUGS_CONFIG:/artbugs.json:ro" \
        -v "$parent:$container_parent" \
        -e CIRCOM_ARTIFICIAL_BUGS_CONFIG=/artbugs.json \
        --memory "$CONTAINER_MEMORY" \
        --memory-swap "$CONTAINER_MEMORY_SWAP" \
        "$IMAGE_CIRCUZZ" \
        python3 cli.py explore \
            --tool circom \
            -v3 \
            --timeout "$TOOL_TIMEOUT" \
            --working-dir /tmp/artbugs-circuzz/working \
            --report-dir "$container_report" \
            --seed 43535 \
            --config "$config_rel" \
        2>&1 | tee "$log"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

case "$TOOL" in
    smt-bool)
        run_smt "smt_bool"
        ;;
    smt-ff)
        run_smt "smt_ff"
        ;;
    circuzz-picus)
        run_circuzz "fyp_experiments/artificial-bugs/configs/picus.json" "picus"
        ;;
    circuzz-standard)
        run_circuzz "fyp_experiments/artificial-bugs/configs/standard.json" "standard"
        ;;
esac

echo ""
echo "Done. Results in: $OBJ_DIR"
echo ""
echo "Report: python3 $SCRIPT_DIR/watch.py $OBJ_DIR"
