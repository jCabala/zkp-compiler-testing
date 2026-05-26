#!/usr/bin/env bash
#
# Collect Circom compiler coverage for bool-circom and ff-circom benchmarks
# and generate a differential coverage report.
#
# Requires the LLVM-instrumented Circom image:
#   localhost/smt-exp-circom-coverage:latest
#
# Usage: ./coverage.sh
#   DURATION=120 ./coverage.sh   # override experiment duration (default 60s)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "$SCRIPT_DIR/../..")"
COVERAGE_ROOT="$REPO_ROOT/evaluation/coverage"
OBJ_DIR="$SCRIPT_DIR/obj/coverage"
source "$REPO_ROOT/smt-solver/experiments/common.sh"

IMAGE_CIRCOM_COVERAGE="localhost/smt-exp-circom-coverage:latest"
DURATION="${DURATION:-900}"
SOLVER="cvc5"
ORACLE="sat"
CONFIG="/workspace/smt-solver/experiments/legacy/sat_fusion/sat_fusion_config.txt"
YY_SEED="7586"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-64g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"

BOOL_SMT="$REPO_ROOT/smt-solver/benchmarks/core/sat"
FF_SMT="$REPO_ROOT/smt-solver/benchmarks/finite-field/sat"

to_container_path() {
    local p="$1"
    if [[ "$p" == "$REPO_ROOT"* ]]; then
        echo "/workspace${p#$REPO_ROOT}"
    else
        echo "$p"
    fi
}

BOOL_SMT_CTR="$(to_container_path "$BOOL_SMT")"
FF_SMT_CTR="$(to_container_path "$FF_SMT")"

RUN_ID="$(date +%Y%m%d-%H%M%S)-$$"
PROFRAW_ROOT="$OBJ_DIR/profraw/$RUN_ID"
mkdir -p "$PROFRAW_ROOT/bool" "$PROFRAW_ROOT/ff"

generate_report() {
    local profraw_dir="$1"
    local experiment="$2"
    echo "[coverage] Generating report for $experiment..." >&2
    podman run --rm \
        -v "$REPO_ROOT":/workspace \
        -v "$profraw_dir":/coverage/profraw \
        --workdir /workspace/evaluation/coverage \
        -e IN_PODMAN=1 \
        "$IMAGE_CIRCOM_COVERAGE" \
        bash -lc "./generate_report.sh $experiment"
}

run_coverage_container() {
    local label="$1"
    local benchmarks_ctr="$2"
    local profraw_dir="$3"
    local tmp_dir="/workspace/smt-solver/experiments/tmp_bool_vs_ff_${label}"

    echo "[coverage] Starting $label (duration=${DURATION}s)..." >&2

    CLI_COMMAND="python3 /workspace/smt-solver/cli.py solve --zk-dsl circom --solver $SOLVER --tmp-dir $tmp_dir"

    podman run --rm \
        --name "bool-vs-ff-coverage-${label}-$$" \
        -v "$REPO_ROOT":/workspace \
        -v "$profraw_dir":/coverage/profraw \
        --workdir /workspace/evaluation/bool-vs-ff \
        --memory "$CONTAINER_MEMORY" \
        --memory-swap "$CONTAINER_MEMORY_SWAP" \
        -e IN_PODMAN=1 \
        -e BENCHMARKS="$benchmarks_ctr" \
        -e TMP_DIR="$tmp_dir" \
        -e DURATION="$DURATION" \
        -e TIMEOUT="$DURATION" \
        -e ORACLE="$ORACLE" \
        -e SOLVER="$SOLVER" \
        -e WARMUP_SOLVER="$SOLVER" \
        -e CONFIG="$CONFIG" \
        -e YY_SEED="$YY_SEED" \
        -e COVERAGE_MODE_NAME="$label" \
        -e CLI_COMMAND="$CLI_COMMAND" \
        -e OUT_FILE="$OBJ_DIR/${label}.out" \
        -e YY_CONFIG="$CONFIG" \
        -e YY_LOG_DIR="$OBJ_DIR/${label}/logs" \
        -e YY_SCRATCH_DIR="$OBJ_DIR/${label}/scratch" \
        -e YY_BUG_DIR="$OBJ_DIR/${label}/bugs" \
        "$IMAGE_CIRCOM_COVERAGE" \
        bash -lc "
            source /workspace/smt-solver/experiments/common.sh
            mkdir -p \$YY_LOG_DIR \$YY_SCRATCH_DIR \$YY_BUG_DIR
            run_yinyang_experiment &
            YY_PID=\$!
            sleep $DURATION
            kill \$YY_PID 2>/dev/null || true
            wait \$YY_PID 2>/dev/null || true
        "
}

# ── Run bool and ff in parallel ───────────────────────────────────────────────

echo "[coverage] Running bool and ff coverage in parallel (${DURATION}s each)..." >&2

run_coverage_container "bool" "$BOOL_SMT_CTR" "$PROFRAW_ROOT/bool" &
BOOL_PID=$!

run_coverage_container "ff" "$FF_SMT_CTR" "$PROFRAW_ROOT/ff" &
FF_PID=$!

trap 'kill $BOOL_PID $FF_PID 2>/dev/null; exit 1' INT TERM

wait $BOOL_PID && echo "[coverage] bool done" || echo "[coverage] bool failed"
wait $FF_PID   && echo "[coverage] ff done"   || echo "[coverage] ff failed"
trap - INT TERM

# ── Generate per-experiment reports ──────────────────────────────────────────

mkdir -p "$COVERAGE_ROOT/obj/bool-vs-ff-bool"
mkdir -p "$COVERAGE_ROOT/obj/bool-vs-ff-ff"

ln -sfn "$PROFRAW_ROOT/bool" "$COVERAGE_ROOT/obj/bool-vs-ff-bool/profraw" 2>/dev/null || \
    cp -r "$PROFRAW_ROOT/bool" "$COVERAGE_ROOT/obj/bool-vs-ff-bool/profraw"

ln -sfn "$PROFRAW_ROOT/ff"   "$COVERAGE_ROOT/obj/bool-vs-ff-ff/profraw"   2>/dev/null || \
    cp -r "$PROFRAW_ROOT/ff"   "$COVERAGE_ROOT/obj/bool-vs-ff-ff/profraw"

generate_report "$PROFRAW_ROOT/bool" "bool-vs-ff-bool"
generate_report "$PROFRAW_ROOT/ff"   "bool-vs-ff-ff"

# ── Differential report ───────────────────────────────────────────────────────

echo "[coverage] Generating differential report..." >&2
podman run --rm \
    -v "$REPO_ROOT":/workspace \
    --workdir /workspace/evaluation/coverage \
    -e IN_PODMAN=1 \
    "$IMAGE_CIRCOM_COVERAGE" \
    bash -lc "python3 generate_diff_report.py bool-vs-ff-bool bool-vs-ff-ff"

echo ""
echo "Reports:"
echo "  Bool:  $COVERAGE_ROOT/obj/bool-vs-ff-bool/coverage_report/html/index.html"
echo "  FF:    $COVERAGE_ROOT/obj/bool-vs-ff-ff/coverage_report/html/index.html"
echo "  Diff:  serve with: cd $COVERAGE_ROOT && ./serve_report.sh diff bool-vs-ff-bool bool-vs-ff-ff"
