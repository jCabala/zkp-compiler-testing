#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
source "$SCRIPT_DIR/../common.sh"

ORACLE="sat" # sat or unsat
BENCHMARKS_CIRCOM="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/"
TIMEOUT="30" # seconds
SOLVER="picus" # z3 or cvc5 or picus
# PRUNE_CIRCOM="7" # If want to use add to command
# PRUNE_SEED="5675"
CONFIG="./circom_artificial_bugs_config.txt"
YY_SEED="7586"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-64g}"
CONTAINER_MEMORY_SWAP="${CONTAINER_MEMORY_SWAP:--1}"

if [[ "${IN_PODMAN:-0}" != "1" ]]; then
  targets=("$@")
  if [[ ${#targets[@]} -eq 0 ]]; then
    targets=("circom")
  fi

  pids=()
  labels=()

  for target in "${targets[@]}"; do
    case "$target" in
      circom|circuzz)
        dsl="circom"
        run_label="circom"
        benchmarks="$BENCHMARKS_CIRCOM"
        ;;
      *)
        echo "unsupported target '$target' (use: circom)" >&2
        exit 1
        ;;
    esac

    container_name="circom-artificial-bugs-${run_label}-$$"
    benchmarks_container="$benchmarks"
    if [[ "$benchmarks_container" == "$REPO_ROOT"* ]]; then
      benchmarks_container="/workspace${benchmarks_container#$REPO_ROOT}"
    fi

    DSL="$dsl"
    image=$(_select_image_for_dsl)
    podman run --rm \
      --name "$container_name" \
      -v "$REPO_ROOT":/workspace \
      --workdir /workspace/smt-solver/experiments/circom-artificial-bugs \
      --memory "$CONTAINER_MEMORY" \
      --memory-swap "$CONTAINER_MEMORY_SWAP" \
      -e IN_PODMAN=1 \
      -e YY_SEED \
      -e BENCHMARKS="$benchmarks_container" \
      -e BUG_CONFIG \
      -e TMP_DIR \
      -e IMAGE_CIRCOM -e IMAGE_GNARK \
      "$image" \
      bash -lc "./circom_artificial_bugs.sh --in-container $dsl $run_label" &
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

DSL="${2:-circom}"       # circom only
RUN_LABEL="${3:-$DSL}"   # used for output/log folder names
TMP_DIR="${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}"
if [[ -z "${BENCHMARKS:-}" ]]; then
  BENCHMARKS="$BENCHMARKS_CIRCOM"
fi

# Force this experiment to use dedicated artificial-bugs circom compiler.
ARTIFICIAL_CIRCOM_ROOT="/workspace/smt-solver/third_party/artificial-bugs/circom"
CIRCOM_BIN="${CIRCOM_BIN:-$ARTIFICIAL_CIRCOM_ROOT/target/release/circom}"
EXPECTED_CIRCOM_BIN="$ARTIFICIAL_CIRCOM_ROOT/target/release/circom"
EXPECTED_HELP_MARKER="artificial-bugs-build"
BUG_CONFIG="${BUG_CONFIG:-$SCRIPT_DIR/artificial_bugs_config.json}"
if [[ ! -x "$CIRCOM_BIN" ]]; then
  echo "missing circom binary at '$CIRCOM_BIN'" >&2
  echo "build it first, e.g.: (cd $ARTIFICIAL_CIRCOM_ROOT && cargo build --release)" >&2
  exit 1
fi
export PATH="$(dirname "$CIRCOM_BIN"):$PATH"

RESOLVED_WHICH_CIRCOM="$(readlink -f "$(which circom)")"
RESOLVED_EXPECTED_CIRCOM="$(readlink -f "$EXPECTED_CIRCOM_BIN")"
if [[ "$RESOLVED_WHICH_CIRCOM" != "$RESOLVED_EXPECTED_CIRCOM" ]]; then
  echo "wrong circom binary in PATH" >&2
  echo "  expected: $RESOLVED_EXPECTED_CIRCOM" >&2
  echo "  actual:   $RESOLVED_WHICH_CIRCOM" >&2
  exit 1
fi
VERSION_OUTPUT="$(circom --version 2>&1 || true)"
HELP_OUTPUT="$(circom --help 2>&1 || true)"
echo "[preflight] circom=$(which circom)" >&2
echo "[preflight] circom --version => $VERSION_OUTPUT" >&2
if [[ "$HELP_OUTPUT" != *"$EXPECTED_HELP_MARKER"* ]]; then
  echo "circom help marker check failed (missing '$EXPECTED_HELP_MARKER')" >&2
  exit 1
fi
if [[ ! -f "$BUG_CONFIG" ]]; then
  echo "missing bug config file at '$BUG_CONFIG'" >&2
  exit 1
fi
export CIRCOM_ARTIFICIAL_BUGS_CONFIG="$BUG_CONFIG"
echo "[preflight] bug-config => $CIRCOM_ARTIFICIAL_BUGS_CONFIG" >&2

CLI_COMMAND="python3 /workspace/smt-solver/cli.py solve --zk-dsl $DSL --solver $SOLVER --tmp-dir $TMP_DIR"
YY_CONFIG="$CONFIG"
OUT_FILE="./obj/circom_artificial_bugs_${RUN_LABEL}.out"
YY_LOG_DIR="./obj/${RUN_LABEL}/logs"
YY_SCRATCH_DIR="./obj/${RUN_LABEL}/scratch"
YY_BUG_DIR="./obj/${RUN_LABEL}/bugs"

cd "$SCRIPT_DIR"
run_yinyang_experiment
