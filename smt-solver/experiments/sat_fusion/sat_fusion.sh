#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
source "$SCRIPT_DIR/../common.sh"

ORACLE="sat" # sat or unsat
BENCHMARKS_CIRCOM="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/"
BENCHMARKS_GNARK="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/unique_sat_2vars_2000/"
TIMEOUT="30" # seconds
SOLVER="z3" # z3 or cvc5 or picus
# PRUNE_CIRCOM="7" # If want to use add to command
# PRUNE_GNARK="4"
# PRUNE_SEED="5675" 
CONFIG="./sat_fusion_config.txt"
YY_SEED="7586"
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
        benchmarks="$BENCHMARKS_GNARK"
        ;;
      circom|circuzz)
        dsl="circom"
        run_label="circom"
        benchmarks="$BENCHMARKS_CIRCOM"
        ;;
      *)
        echo "unsupported target '$target' (use: gnark|circom)" >&2
        exit 1
        ;;
    esac

    container_name="sat-fusion-${run_label}-$$"
    benchmarks_container="$benchmarks"
    if [[ "$benchmarks_container" == "$REPO_ROOT"* ]]; then
      benchmarks_container="/workspace${benchmarks_container#$REPO_ROOT}"
    fi
    DSL="$dsl"
    image=$(_select_image_for_dsl)
    podman run --rm \
      --name "$container_name" \
      -v "$REPO_ROOT":/workspace \
      --workdir /workspace/smt-solver/experiments/sat_fusion \
      --memory "$CONTAINER_MEMORY" \
      --memory-swap "$CONTAINER_MEMORY_SWAP" \
      -e IN_PODMAN=1 \
      -e YY_SEED \
      -e BENCHMARKS="$benchmarks_container" \
      -e TMP_DIR \
      -e IMAGE_CIRCOM -e IMAGE_GNARK \
      "$image" \
      bash -lc "./sat_fusion.sh --in-container $dsl $run_label" &
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
TMP_DIR="${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}"
# If BENCHMARKS was not explicitly provided, pick a default by DSL.
if [[ -z "${BENCHMARKS:-}" ]]; then
  if [[ "$DSL" == "gnark" ]]; then
    BENCHMARKS="$BENCHMARKS_GNARK"
  else
    BENCHMARKS="$BENCHMARKS_CIRCOM"
  fi
fi

# PRUNE="$PRUNE_GNARK"
# if [[ "$DSL" == "circom" ]]; then
#   PRUNE="$PRUNE_CIRCOM"
# fi

CLI_COMMAND="python3 /workspace/smt-solver/cli.py solve --zk-dsl $DSL --solver $SOLVER --tmp-dir $TMP_DIR"
YY_CONFIG="$CONFIG"
OUT_FILE="./obj/sat_fusion_${RUN_LABEL}.out"
YY_LOG_DIR="./obj/${RUN_LABEL}/logs"
YY_SCRATCH_DIR="./obj/${RUN_LABEL}/scratch"
YY_BUG_DIR="./obj/${RUN_LABEL}/bugs"

cd "$SCRIPT_DIR"
run_yinyang_experiment
