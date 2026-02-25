#!/usr/bin/env bash
set -euo pipefail

COMMON_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
REPO_ROOT=$(realpath "$COMMON_DIR/../..")

IMAGE_CIRCOM="${IMAGE_CIRCOM:-localhost/smt-exp-circom:latest}"
IMAGE_GNARK="${IMAGE_GNARK:-localhost/smt-exp-gnark:latest}"

_select_image_for_dsl() {
  case "${DSL:?DSL must be set}" in
    circom) echo "$IMAGE_CIRCOM" ;;
    gnark) echo "$IMAGE_GNARK" ;;
    *)
      echo "unsupported DSL '${DSL}' (use circom|gnark)" >&2
      exit 1
      ;;
  esac
}

run_in_podman_if_needed() {
  local script_rel_path="$1"
  local script_dir_rel
  local script_name
  script_dir_rel=$(dirname "$script_rel_path")
  script_name=$(basename "$script_rel_path")

  if [[ "${IN_PODMAN:-0}" == "1" ]]; then
    return
  fi

  local image
  image=$(_select_image_for_dsl)

  local -a args=(
    podman run --rm
    -v "$REPO_ROOT":/workspace
    --workdir "/workspace/smt-solver/experiments/${script_dir_rel}"
    -e IN_PODMAN=1
  )

  # Pass through all common experiment knobs if set.
  local var
  for var in \
    ORACLE TIMEOUT BENCHMARKS SOLVER DSL BOOL_ONLY PRUNE PRUNE_SEED \
    CONFIG FUSION_REWRITE_POLICY FUSION_SIDE_POLICY \
    IMAGE_CIRCOM IMAGE_GNARK CLI_COMMAND OUT_FILE YY_CONFIG \
    YY_LOG_DIR YY_SCRATCH_DIR YY_BUG_DIR YY_SEED TMP_DIR
  do
    if [[ -v "$var" ]]; then
      args+=( -e "$var" )
    fi
  done

  args+=( "$image" bash -lc "./${script_name}" )
  "${args[@]}"
  exit $?
}

run_yinyang_experiment() {
  : "${ORACLE:?ORACLE must be set}"
  : "${TIMEOUT:?TIMEOUT must be set}"
  : "${BENCHMARKS:?BENCHMARKS must be set}"
  : "${CLI_COMMAND:?CLI_COMMAND must be set}"

  local yy_root="/workspace/smt-solver/third_party/yinyang"
  local out_file="${OUT_FILE:-./obj/experiment.out}"
  local log_dir="${YY_LOG_DIR:-./obj/logs}"
  local scratch_dir="${YY_SCRATCH_DIR:-./obj/scratch}"
  local bug_dir="${YY_BUG_DIR:-./obj/bugs}"

  mkdir -p ./obj "$log_dir" "$scratch_dir" "$bug_dir" "$(dirname "$out_file")"

  # Warm Python/pySMT/backend startup caches once per container before yinyang's
  # per-call timeout starts killing cold starts.
  if [[ "${WARMUP_CLI:-1}" == "1" ]]; then
    local warm_dir="${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}/warmup"
    local warm_sat="$warm_dir/warm_sat.smt2"
    local warm_unsat="$warm_dir/warm_unsat.smt2"
    local warm_solver="${WARMUP_SOLVER:-z3}"
    local warm_dsl="${DSL:-circom}"

    mkdir -p "$warm_dir"
    cat > "$warm_sat" <<'EOF'
(set-logic QF_BV)
(declare-fun x () Bool)
(assert x)
(check-sat)
EOF
    cat > "$warm_unsat" <<'EOF'
(set-logic QF_BV)
(declare-fun x () Bool)
(assert x)
(assert (not x))
(check-sat)
EOF

    echo "[warmup] starting cli warmup (dsl=$warm_dsl solver=$warm_solver tmp=$warm_dir)" >&2
    python3 /workspace/smt-solver/cli.py solve \
      --zk-dsl "$warm_dsl" \
      --solver "$warm_solver" \
      --tmp-dir "${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}" \
      "$warm_sat" >/dev/null 2>&1 || true
    python3 /workspace/smt-solver/cli.py solve \
      --zk-dsl "$warm_dsl" \
      --solver "$warm_solver" \
      --tmp-dir "${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}" \
      "$warm_unsat" >/dev/null 2>&1 || true
    echo "[warmup] completed" >&2
  fi

  local -a cmd=(
    python3 "$yy_root/yinyang_cli.py" "$CLI_COMMAND"
    --oracle "$ORACLE"
    --timeout "$TIMEOUT"
  )
  if [[ -n "${YY_CONFIG:-}" ]]; then
    cmd+=( -c "$YY_CONFIG" )
  fi
  if [[ -n "${YY_SEED:-}" ]]; then
    cmd+=( --seed "$YY_SEED" )
  fi
  cmd+=( --logfolder "$log_dir" --scratchfolder "$scratch_dir" --bugsfolder "$bug_dir" "$BENCHMARKS" )

  local -a env_prefix=("PYTHONPATH=$yy_root")
  if [[ -n "${FUSION_REWRITE_POLICY:-}" ]]; then
    env_prefix+=("YY_FUSION_REWRITE_POLICY=$FUSION_REWRITE_POLICY")
  fi
  if [[ -n "${FUSION_SIDE_POLICY:-}" ]]; then
    env_prefix+=("YY_FUSION_SIDE_POLICY=$FUSION_SIDE_POLICY")
  fi

  local ts
  ts="$(date +%Y%m%d-%H%M%S)-$$"
  local cfg_file="./obj/run_config_${ts}.env"
  {
    echo "# Auto-generated experiment config snapshot"
    echo "timestamp=${ts}"
    echo "pwd=$(pwd)"
    for var in \
      ORACLE TIMEOUT BENCHMARKS SOLVER DSL BOOL_ONLY PRUNE PRUNE_SEED \
      CONFIG FUSION_REWRITE_POLICY FUSION_SIDE_POLICY \
      IMAGE_CIRCOM IMAGE_GNARK CLI_COMMAND OUT_FILE YY_CONFIG \
      YY_LOG_DIR YY_SCRATCH_DIR YY_BUG_DIR YY_SEED TMP_DIR IN_PODMAN
    do
      if [[ -v "$var" ]]; then
        printf '%s=%q\n' "$var" "${!var}"
      fi
    done
    printf 'YINYANG_CMD='
    printf '%q ' "${cmd[@]}"
    printf '\n'
  } > "$cfg_file"

  env "${env_prefix[@]}" "${cmd[@]}" > "$out_file" 2>&1
}
