#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
source "$SCRIPT_DIR/../common.sh"

ORACLE="sat" # sat or unsat
BENCHMARKS="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/"
TIMEOUT="30" # seconds

FUSION_REWRITE_POLICY="all"
FUSION_SIDE_POLICY="one"
SOLVER="picus"
CONFIG="./picus_fusion_config.txt"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-4g}"
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
        label="gnark"
        ;;
      circom|circuzz)
        dsl="circom"
        label="circom"
        ;;
      *)
        echo "unsupported target '$target' (use: gnark|circom)" >&2
        exit 1
        ;;
    esac

    DSL="$dsl"
    image=$(_select_image_for_dsl)
    podman run --rm \
      -v "$REPO_ROOT":/workspace \
      --workdir /workspace/smt-solver/experiments/picus_fusion \
      --memory "$CONTAINER_MEMORY" \
      --memory-swap "$CONTAINER_MEMORY_SWAP" \
      -e IN_PODMAN=1 \
      -e IMAGE_CIRCOM -e IMAGE_GNARK \
      "$image" \
      bash -lc "./picus_fusion.sh --in-container $dsl $label" &
    pids+=("$!")
    labels+=("$label")
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

CLI_COMMAND="python3.11 /workspace/smt-solver/cli.py solve --zk-dsl $DSL --solver $SOLVER --tmp-dir /workspace/smt-solver/experiments/tmp_fusion/"
YY_CONFIG="$CONFIG"
OUT_FILE="./obj/picus_fusion_${RUN_LABEL}.out"
YY_LOG_DIR="./obj/${RUN_LABEL}/logs"
YY_SCRATCH_DIR="./obj/${RUN_LABEL}/scratch"
YY_BUG_DIR="./obj/${RUN_LABEL}/bugs"

cd "$SCRIPT_DIR"
run_yinyang_experiment
