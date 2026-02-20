#!/bin/bash

#
# Runs SMT-fusion pipeline experiments in Podman containers.
# Usage:
#   ./explore.sh                    # runs circom,gnark,noir
#   ./explore.sh circom noir        # runs selected tools only
#

set -euo pipefail
set -x

start=$(date +%s)

SCRIPT_PATH=$(dirname "$(realpath "$0")")
CIRCUZZ_ROOT=$(realpath "$SCRIPT_PATH/../../")
REPO_ROOT=$(realpath "$CIRCUZZ_ROOT/..")

# =================================================
#                  Configuration
# =================================================

CIRCOM_CONFIG="fyp_experiments/smt-fusion/config/circom.json"
GNARK_CONFIG="fyp_experiments/smt-fusion/config/gnark.json"
NOIR_CONFIG="fyp_experiments/smt-fusion/config/noir.json"

IMAGE_CIRCOM_DEFAULT="localhost/circom-latest:latest"
IMAGE_GNARK_DEFAULT="localhost/gnark-latest:latest"
IMAGE_NOIR_DEFAULT="localhost/noir-latest-patched:latest"

SEED=2123
VERBOSITY=2
USE_TMP=1
CIRCOM_MEMORY_LIMIT="4g"
GNARK_MEMORY_LIMIT="4g"
NOIR_MEMORY_LIMIT="4g"

# Timeout settings
T_SECONDS=0
T_MINUTES=0
T_HOURS=48

CIRCOM_NUM=1
GNARK_NUM=1
NOIR_NUM=1

CIRCOM_CPUS=2
GNARK_CPUS=2
NOIR_CPUS=2

WAIT_BETWEEN=1
TMP_DIR="/tmp/circuzz/seed-$SEED-date-$start"
OBJ_DIR="$SCRIPT_PATH/obj/seed-$SEED-date-$start"

# Tools can be selected via args, defaults to all.
if [[ $# -gt 0 ]]; then
  TOOLS=("$@")
else
  TOOLS=("circom" "gnark" "noir")
fi

# =================================================
#                 Implementation
# =================================================

PODMAN_TIMEOUT=$((($T_HOURS * 60 * 60) + (($T_MINUTES + 5) * 60) + $T_SECONDS))
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)

cd "$SCRIPT_PATH"

RANDOM=$SEED
mkdir -p "$OBJ_DIR"
if [[ $USE_TMP -eq 1 ]]; then
  mkdir -p "$TMP_DIR"
fi

start_tool() {
  local tool="$1"
  local image="$2"
  local run_name="$3"
  local cpus="$4"
  local memory_limit="$5"
  local run_seed="$6"

  local config
  case "$tool" in
    circom) config="$CIRCOM_CONFIG" ;;
    gnark)  config="$GNARK_CONFIG" ;;
    noir)   config="$NOIR_CONFIG" ;;
    *) echo "unknown tool $tool"; exit 1 ;;
  esac

  local exp_report_dir="$OBJ_DIR/$run_name/explore/report"
  local log_dir_run="$OBJ_DIR/$run_name/explore/logs"
  local prefixed_report_dir="/workspace/circuzz/fyp_experiments/smt-fusion/obj/seed-$SEED-date-$start/$run_name/explore/report"
  local exp_work_dir
  if [[ $USE_TMP -eq 1 ]]; then
    exp_work_dir="/tmp/$run_name/explore/working"
  else
    exp_work_dir="/workspace/circuzz/fyp_experiments/smt-fusion/obj/seed-$SEED-date-$start/$run_name/explore/working"
  fi

  mkdir -p "$exp_report_dir" "$log_dir_run"

  # Mount repo root so both /workspace/circuzz and /workspace/smt-solver are available.
  if [[ $USE_TMP -eq 1 ]]; then
    podman run --timeout="$PODMAN_TIMEOUT" --pids-limit=-1 --cpus="$cpus" --memory="$memory_limit" \
      -v "$REPO_ROOT":/workspace -v "$TMP_DIR":/tmp --workdir /workspace/circuzz --rm "$image" \
      python3 cli.py explore --tool "$tool" -v"$VERBOSITY" --timeout "$TOOL_TIMEOUT" \
      --working-dir "$exp_work_dir" --report-dir "$prefixed_report_dir" --seed "$run_seed" --config "$config" \
      > "$log_dir_run/$run_name-explore.log" 2>&1
  else
    podman run --timeout="$PODMAN_TIMEOUT" --pids-limit=-1 --cpus="$cpus" --memory="$memory_limit" \
      -v "$REPO_ROOT":/workspace --workdir /workspace/circuzz --rm "$image" \
      python3 cli.py explore --tool "$tool" -v"$VERBOSITY" --timeout "$TOOL_TIMEOUT" \
      --working-dir "$exp_work_dir" --report-dir "$prefixed_report_dir" --seed "$run_seed" --config "$config" \
      > "$log_dir_run/$run_name-explore.log" 2>&1
  fi
}

run_group() {
  local tool="$1"
  local image="$2"
  local num="$3"
  local cpus="$4"
  local memory_limit="$5"
  if [[ $num -eq 0 ]]; then
    return
  fi
  local pids=()
  for i in $(seq 1 "$num"); do
    local r="$RANDOM"
    start_tool "$tool" "$image" "$tool-$i" "$cpus" "$memory_limit" "$r" &
    pids+=($!)
    echo "Started $tool $i/$num with seed $r ..."
    sleep "$WAIT_BETWEEN"
  done
  wait "${pids[@]}"
}

tool_pids=()
tool_names=()
for tool in "${TOOLS[@]}"; do
  case "$tool" in
    circom)
      run_group circom "$IMAGE_CIRCOM_DEFAULT" "$CIRCOM_NUM" "$CIRCOM_CPUS" "$CIRCOM_MEMORY_LIMIT" &
      ;;
    gnark)
      run_group gnark "$IMAGE_GNARK_DEFAULT" "$GNARK_NUM" "$GNARK_CPUS" "$GNARK_MEMORY_LIMIT" &
      ;;
    noir)
      run_group noir "$IMAGE_NOIR_DEFAULT" "$NOIR_NUM" "$NOIR_CPUS" "$NOIR_MEMORY_LIMIT" &
      ;;
    *)
      echo "unsupported tool selector '$tool' (use: circom gnark noir)"
      exit 1
      ;;
  esac
  tool_pids+=($!)
  tool_names+=("$tool")
done

overall_status=0
for idx in "${!tool_pids[@]}"; do
  pid="${tool_pids[$idx]}"
  name="${tool_names[$idx]}"
  if wait "$pid"; then
    echo "tool group '$name' finished successfully"
  else
    echo "tool group '$name' failed"
    overall_status=1
  fi
done

if [[ $USE_TMP -eq 1 ]]; then
  rm -rf "$TMP_DIR"
fi

end=$(date +%s)
runtime=$((end - start))
echo "finished in $runtime s"
exit "$overall_status"
