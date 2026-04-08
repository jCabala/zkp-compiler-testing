#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
source "$SCRIPT_DIR/../common.sh"

ORACLE="sat" # sat or unsat
BENCHMARKS="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/"
TIMEOUT="60"       # seconds (yinyang per-call timeout, circom)
TIMEOUT_GNARK="60" # seconds (yinyang per-call timeout, gnark)

FUSION_REWRITE_POLICY="all"
FUSION_SIDE_POLICY="one"
SOLVER="picus"
CONFIG="./picus_fusion_config.txt"
YY_SEED="5959"
WITHOUT_HINTS="" # e.g. --without-hints (hints are on by default)
CONTAINER_MEMORY="${CONTAINER_MEMORY:-64g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"

if [[ "${IN_PODMAN:-0}" != "1" ]]; then
  targets=("$@")
  if [[ ${#targets[@]} -eq 0 ]]; then
    targets=("gnark" "circom")
  fi

  pids=()
  labels=()

  for target in "${targets[@]}"; do
    case "$target" in
      gnark)
        dsl="gnark"
        run_label="gnark"
        ;;
      circom|circuzz)
        dsl="circom"
        run_label="circom"
        ;;
      *)
        echo "unsupported target '$target' (use: gnark|circom)" >&2
        exit 1
        ;;
    esac

    container_name="picus-fusion-${run_label}-$$"
    DSL="$dsl"
    image=$(_select_image_for_dsl)
    podman run --rm \
      --name "$container_name" \
      -v "$REPO_ROOT":/workspace \
      --workdir /workspace/smt-solver/experiments/picus_fusion \
      --memory "$CONTAINER_MEMORY" \
      --memory-swap "$CONTAINER_MEMORY_SWAP" \
      -e IN_PODMAN=1 \
      -e YY_SEED \
      -e TMP_DIR \
      -e GOCACHE=/workspace/smt-solver/experiments/obj/go-cache \
      -e IMAGE_CIRCOM -e IMAGE_GNARK \
      "$image" \
      bash -lc "./picus_fusion.sh --in-container $dsl $run_label" &
    pids+=("$!")
    labels+=("${run_label} (seed=$YY_SEED)")
  done

  overall_status=0
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
      echo "target '${labels[$i]}' failed" >&2
      overall_status=1
    fi
  done
  exit "$overall_status"
fi

if [[ "${1:-}" != "--in-container" ]]; then
  echo "container mode expects: --in-container <dsl> <label>" >&2
  exit 1
fi

DSL="${2:-gnark}"          # gnark|circom
RUN_LABEL="${3:-$DSL}"     # used for output/log folder names
TMP_DIR="${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}/$DSL"

CLI_COMMAND="python3 /workspace/smt-solver/cli.py solve --config /workspace/smt-solver/experiments/picus_fusion/solve_config.json --zk-dsl $DSL --tmp-dir $TMP_DIR $WITHOUT_HINTS"
YY_CONFIG="$CONFIG"
OUT_FILE="./obj/picus_fusion_${RUN_LABEL}.out"
YY_LOG_DIR="./obj/${RUN_LABEL}/logs"
YY_SCRATCH_DIR="./obj/${RUN_LABEL}/scratch"
YY_BUG_DIR="./obj/${RUN_LABEL}/bugs"

cd "$SCRIPT_DIR"
run_yinyang_experiment
