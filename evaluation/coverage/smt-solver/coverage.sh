#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
COVERAGE_ROOT=$(realpath "$SCRIPT_DIR/..")
OBJ_ROOT="$COVERAGE_ROOT/obj"
OBJ_DIR="$OBJ_ROOT/smt-solver"
source "$SCRIPT_DIR/../../../smt-solver/experiments/common.sh"

# --- Experiment parameters ---
BENCHMARKS_CIRCOM=$(realpath "$SCRIPT_DIR/../../../smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/")
TIMEOUT="30"  # seconds
COVERAGE_VARIANTS="${COVERAGE_VARIANTS:-sat,picus}"
SAT_SOLVER="${SAT_SOLVER:-z3}"      # z3 or cvc5 or picus
SAT_CONFIG="${SAT_CONFIG:-/workspace/smt-solver/experiments/sat_fusion/sat_fusion_config.txt}"
SAT_YY_SEED="${SAT_YY_SEED:-7586}"
PICUS_SOLVER="${PICUS_SOLVER:-picus}"
PICUS_CONFIG="${PICUS_CONFIG:-/workspace/smt-solver/experiments/picus_fusion/picus_fusion_config.txt}"
PICUS_YY_SEED="${PICUS_YY_SEED:-9855}"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-64g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"
DURATION="${DURATION:-60}"  # overall experiment duration in seconds

# This experiment only works with the coverage-instrumented Circom image.
IMAGE_CIRCOM_COVERAGE="localhost/smt-exp-circom-coverage:latest"

parse_variants() {
  IFS=',' read -r -a RAW_VARIANTS <<< "$COVERAGE_VARIANTS"
  VARIANTS=()
  for variant in "${RAW_VARIANTS[@]}"; do
    variant="${variant//[[:space:]]/}"
    [[ -n "$variant" ]] || continue
    case "$variant" in
      sat|sat_fusion) VARIANTS+=("sat_fusion") ;;
      picus|picus_fusion) VARIANTS+=("picus_fusion") ;;
      *)
        echo "ERROR: unsupported coverage variant '$variant' (use sat or picus)" >&2
        exit 1
        ;;
    esac
  done

  if [[ "${#VARIANTS[@]}" -eq 0 ]]; then
    echo "ERROR: no coverage variants selected" >&2
    exit 1
  fi
}

configure_variant() {
  local variant="$1"

  ORACLE="sat"
  FUSION_REWRITE_POLICY=""
  FUSION_SIDE_POLICY=""
  WARMUP_SOLVER=""

  case "$variant" in
    sat_fusion)
      COVERAGE_MODE_NAME="sat_fusion"
      SOLVER="$SAT_SOLVER"
      CONFIG="$SAT_CONFIG"
      YY_SEED="$SAT_YY_SEED"
      ;;
    picus_fusion)
      COVERAGE_MODE_NAME="picus_fusion"
      SOLVER="$PICUS_SOLVER"
      CONFIG="$PICUS_CONFIG"
      YY_SEED="$PICUS_YY_SEED"
      FUSION_REWRITE_POLICY="all"
      FUSION_SIDE_POLICY="one"
      ;;
    *)
      echo "ERROR: unsupported configured variant '$variant'" >&2
      exit 1
      ;;
  esac

  WARMUP_SOLVER="$SOLVER"
}

generate_coverage_from_profraw_dir() {
  local profraw_dir="$1"
  local experiment="$2"

  echo "" >&2
  echo "[coverage] Generating coverage report for $experiment..." >&2

  podman run --rm \
    -v "$REPO_ROOT":/workspace \
    -v "$profraw_dir":/coverage/profraw \
    --workdir /workspace/evaluation/coverage \
    -e IN_PODMAN=1 \
    "$IMAGE_CIRCOM_COVERAGE" \
    bash -lc "./generate_report.sh $experiment"
}

# ---------- HOST MODE ----------
if [[ "${IN_PODMAN:-0}" != "1" ]]; then
  DSL="circom"
  image="$IMAGE_CIRCOM_COVERAGE"
  parse_variants

  benchmarks="$BENCHMARKS_CIRCOM"
  benchmarks_container="$benchmarks"
  if [[ "$benchmarks_container" == "$REPO_ROOT"* ]]; then
    benchmarks_container="/workspace${benchmarks_container#$REPO_ROOT}"
  fi

  PROFRAW_BASE_DIR="$OBJ_DIR/profraw"
  RUN_ID="$(date +%Y%m%d-%H%M%S)-$$"
  PROFRAW_ROOT="$PROFRAW_BASE_DIR/$RUN_ID"
  mkdir -p "$PROFRAW_ROOT"
  echo "[coverage] Collecting raw coverage under $PROFRAW_ROOT" >&2

  CONTAINER_PIDS=()
  CONTAINER_LABELS=()
  overall_status=0

  cleanup_containers() {
    for pid in "${CONTAINER_PIDS[@]:-}"; do
      kill "$pid" 2>/dev/null || true
    done
  }
  trap cleanup_containers INT TERM

  for variant in "${VARIANTS[@]}"; do
    configure_variant "$variant"

    profraw_dir="$PROFRAW_ROOT/$COVERAGE_MODE_NAME"
    rm -rf "$profraw_dir"
    mkdir -p "$profraw_dir"

    tmp_dir="/workspace/smt-solver/experiments/tmp_fusion_${COVERAGE_MODE_NAME}"
    container_name="coverage-${COVERAGE_MODE_NAME}-$$"

    podman run --rm \
      --name "$container_name" \
      -v "$REPO_ROOT":/workspace \
      -v "$profraw_dir":/coverage/profraw \
      --workdir /workspace/evaluation/coverage/smt-solver \
      --memory "$CONTAINER_MEMORY" \
      --memory-swap "$CONTAINER_MEMORY_SWAP" \
      -e IN_PODMAN=1 \
      -e BENCHMARKS="$benchmarks_container" \
      -e TMP_DIR="$tmp_dir" \
      -e DURATION="$DURATION" \
      -e ORACLE="$ORACLE" \
      -e SOLVER="$SOLVER" \
      -e WARMUP_SOLVER="$WARMUP_SOLVER" \
      -e CONFIG="$CONFIG" \
      -e YY_SEED="$YY_SEED" \
      -e COVERAGE_MODE_NAME="$COVERAGE_MODE_NAME" \
      -e FUSION_REWRITE_POLICY="$FUSION_REWRITE_POLICY" \
      -e FUSION_SIDE_POLICY="$FUSION_SIDE_POLICY" \
      "$image" \
      bash -lc "./coverage.sh --in-container $DSL $DSL" &
    CONTAINER_PIDS+=("$!")
    CONTAINER_LABELS+=("$COVERAGE_MODE_NAME")
  done

  echo "[coverage] Running ${CONTAINER_LABELS[*]} in parallel..." >&2
  for i in "${!CONTAINER_PIDS[@]}"; do
    if ! wait "${CONTAINER_PIDS[$i]}"; then
      echo "[coverage] Variant '${CONTAINER_LABELS[$i]}' failed" >&2
      overall_status=1
    fi
  done
  trap - INT TERM

  if [[ -z "$(find "$PROFRAW_ROOT" -type f -name '*.profraw' -print -quit)" ]]; then
    echo "ERROR: no .profraw files were collected from any coverage variant" >&2
    exit 1
  fi

  for variant in "${VARIANTS[@]}"; do
    configure_variant "$variant"
    profraw_dir="$PROFRAW_ROOT/$COVERAGE_MODE_NAME"
    variant_experiment="${COVERAGE_MODE_NAME}_${DSL}"
    if [[ -n "$(find "$profraw_dir" -type f -name '*.profraw' -print -quit)" ]]; then
      if ! generate_coverage_from_profraw_dir "$profraw_dir" "$variant_experiment"; then
        overall_status=1
      fi
    else
      echo "[coverage] Skipping report for $variant_experiment: no .profraw files collected" >&2
      overall_status=1
    fi
  done

  if ! generate_coverage_from_profraw_dir "$PROFRAW_ROOT" "smt-solver"; then
    exit 1
  fi

  exit "$overall_status"
fi

# ---------- CONTAINER MODE ----------
if [[ "${1:-}" != "--in-container" ]]; then
  echo "container mode expects: --in-container <dsl> <label>" >&2
  exit 1
fi

DSL="${2:-circom}"
RUN_LABEL="${3:-$DSL}"
TMP_DIR="${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}"
if [[ -z "${BENCHMARKS:-}" ]]; then
  BENCHMARKS="$BENCHMARKS_CIRCOM"
fi

echo "[preflight] circom=$(which circom)" >&2
echo "[preflight] image=${IMAGE_CIRCOM_COVERAGE:-<unknown>}" >&2
echo "[preflight] LLVM_PROFILE_FILE=${LLVM_PROFILE_FILE:-<unset>}" >&2
echo "[preflight] profraw dir: /coverage/profraw" >&2

if [[ -z "${LLVM_PROFILE_FILE:-}" || ! -d /coverage/profraw ]]; then
  echo "ERROR: coverage environment is not initialized" >&2
  echo "Run this script from the host so it can launch $IMAGE_CIRCOM_COVERAGE" >&2
  exit 1
fi

rm -f /coverage/profraw/*.profraw

MODE_NAME="${COVERAGE_MODE_NAME:-sat_fusion}"
if [[ -z "${SOLVER:-}" || -z "${CONFIG:-}" || -z "${YY_SEED:-}" ]]; then
  configure_variant "$MODE_NAME"
fi
WARMUP_SOLVER="${WARMUP_SOLVER:-$SOLVER}"
RUN_OBJ_DIR="$OBJ_ROOT/${MODE_NAME}_${RUN_LABEL}"
mkdir -p "$RUN_OBJ_DIR"
OUT_FILE="$OBJ_DIR/coverage_${MODE_NAME}_${RUN_LABEL}.out"
YY_LOG_DIR="$RUN_OBJ_DIR/logs"
YY_SCRATCH_DIR="$RUN_OBJ_DIR/scratch"
YY_BUG_DIR="$RUN_OBJ_DIR/bugs"
CLI_COMMAND="python3 /workspace/smt-solver/cli.py solve --zk-dsl $DSL --solver $SOLVER --tmp-dir $TMP_DIR"
YY_CONFIG="$CONFIG"

cd "$SCRIPT_DIR"

echo "[coverage] Fuzzing for ${DURATION}s in $MODE_NAME (Ctrl-C to stop early)..." >&2

run_yinyang_experiment &
YY_PID=$!

(
  sleep "$DURATION"
  kill "$YY_PID" 2>/dev/null || true
) &
TIMER_PID=$!

wait "$YY_PID" 2>/dev/null || true
kill "$TIMER_PID" 2>/dev/null || true
