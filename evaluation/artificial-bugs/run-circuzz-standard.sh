#!/usr/bin/env bash
#
# Run N parallel circuzz-standard instances with different seeds.
#
# Usage:
#   ./run-circuzz-standard.sh [--bool]
#
# Each instance runs for T_MINUTES (default 5) with a unique seed.
# Results land in obj/run-<timestamp>-circuzz-standard[-bool]/instance-{0..N-1}/
#
# Override examples:
#   N_INSTANCES=3 T_MINUTES=10 ./run-circuzz-standard.sh --bool

set -euo pipefail

BOOL_GENERATOR=0
for arg in "$@"; do
    case "$arg" in
        --bool) BOOL_GENERATOR=1 ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "$SCRIPT_DIR/../..")"
CIRCUZZ_ROOT="$REPO_ROOT/circuzz"
SMT_ROOT="$REPO_ROOT/smt-solver"

ARTBUGS_BIN="$SMT_ROOT/third_party/artificial-bugs/circom/target/release/circom"
ARTBUGS_CONFIG="$SCRIPT_DIR/configs/artbugs.json"

IMAGE_CIRCUZZ="${IMAGE_CIRCUZZ:-circom-latest}"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-16g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"

N_INSTANCES="${N_INSTANCES:-5}"
SEEDS=(43535 12345 67890 11111 99999 55555 77777 33333 21212 98765)

T_MINUTES="${T_MINUTES:-5}"
TOOL_TIMEOUT="0h${T_MINUTES}m0s"
PODMAN_TIMEOUT=$(( (T_MINUTES + 5) * 60 ))

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

if [[ "$BOOL_GENERATOR" -eq 1 ]]; then
    CIRCUZZ_CONFIG="fyp_experiments/artificial-bugs/configs/standard-bool.json"
    RUN_LABEL="circuzz-standard-bool"
else
    CIRCUZZ_CONFIG="fyp_experiments/artificial-bugs/configs/standard.json"
    RUN_LABEL="circuzz-standard"
fi

START=$(date +%s)
OBJ_DIR="$SCRIPT_DIR/obj/run-${START}-${RUN_LABEL}"
mkdir -p "$OBJ_DIR"
echo "circuzz-standard" > "$OBJ_DIR/tool.txt"

echo "[preflight] generator: $([ $BOOL_GENERATOR -eq 1 ] && echo bool || echo arithmetic)"
echo "[preflight] instances: $N_INSTANCES"
echo "[preflight] timeout:   $TOOL_TIMEOUT"
echo "[preflight] output:    $OBJ_DIR"
echo ""

# ── Spawn instances ───────────────────────────────────────────────────────────

PIDS=()
CONTAINER_NAMES=()

for (( i=0; i<N_INSTANCES; i++ )); do
    seed="${SEEDS[$i]}"
    parent="$OBJ_DIR/instance-${i}/circuzz"
    mkdir -p "$parent"

    container_parent="/output_parent"
    container_report="$container_parent/report"
    log="$OBJ_DIR/instance-${i}/run.log"
    container_name="artbugs-circuzz-standard-${i}-$$"
    CONTAINER_NAMES+=("$container_name")

    echo "  Spawning instance $i  (seed=$seed)"
    podman run \
        --timeout="$PODMAN_TIMEOUT" \
        --pids-limit=-1 \
        --rm \
        --name "$container_name" \
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
            --working-dir "/tmp/artbugs-circuzz-${i}/working" \
            --report-dir "$container_report" \
            --seed "$seed" \
            --config "$CIRCUZZ_CONFIG" \
        2>&1 | tee "$log" &
    PIDS+=($!)
done

trap 'echo "Interrupted — killing all instances..."; kill "${PIDS[@]}" 2>/dev/null; exit 1' INT TERM

printf '%s\n' "${CONTAINER_NAMES[@]}" > "$OBJ_DIR/containers.txt"

echo ""
echo "All $N_INSTANCES instances running..."
echo ""

python3 "$SCRIPT_DIR/watch.py" "$OBJ_DIR" &
WATCH_PID=$!

for pid in "${PIDS[@]}"; do
    wait "$pid" || true
done

wait "$WATCH_PID" 2>/dev/null || true

OVERALL_END=$(date +%s)
echo ""
echo "════════════════════════════════════════"
echo "  Done in $(( OVERALL_END - START ))s"
echo "  Results: $OBJ_DIR"
echo "════════════════════════════════════════"
