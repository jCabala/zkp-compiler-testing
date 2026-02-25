#!/bin/bash

#
# Runs two Circom exploration groups in parallel, both using the artificial-bugs
# compiler binary from sibling smt-solver:
#   1) basic arithmetic config
#   2) fully-constraint-circom-style config
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

CIRCOM_CONFIG_BASIC="fyp_experiments/circom-artificial-bugs/config/circom.json"
CIRCOM_CONFIG_FULLY="fyp_experiments/circom-artificial-bugs/config/circom-fully.json"
ARTIFICIAL_BUGS_CONFIG="/workspace/circuzz/fyp_experiments/circom-artificial-bugs/config/artificial_bugs_config.json"
IMAGE_CIRCOM_DEFAULT="localhost/circom-latest:latest"

SEED=43021
VERBOSITY=3
USE_TMP=1

T_SECONDS=0
T_MINUTES=0
T_HOURS=24

# Parallel groups (set either to 0 to disable that group)
CIRCOM_BASIC_NUM=1
CIRCOM_FULLY_NUM=1
CIRCOM_CPUS=4

WAIT_BETWEEN=2
TMP_DIR="/tmp/circuzz/seed-$SEED-date-$start"
OBJ_DIR="$SCRIPT_PATH/obj/seed-$SEED-date-$start"

# Must exist in the mounted /workspace tree.
BUGGY_CIRCOM_DIR="/workspace/smt-solver/third_party/artificial-bugs/circom/target/release"

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

start_one() {
  local run_name="$1"
  local run_seed="$2"
  local config_path="$3"

  local exp_report_dir="$OBJ_DIR/$run_name/explore/report"
  local log_dir_run="$OBJ_DIR/$run_name/explore/logs"
  local prefixed_report_dir="/workspace/circuzz/fyp_experiments/circom-artificial-bugs/obj/seed-$SEED-date-$start/$run_name/explore/report"
  local exp_work_dir
  if [[ $USE_TMP -eq 1 ]]; then
    exp_work_dir="/tmp/$run_name/explore/working"
  else
    exp_work_dir="/workspace/circuzz/fyp_experiments/circom-artificial-bugs/obj/seed-$SEED-date-$start/$run_name/explore/working"
  fi

  mkdir -p "$exp_report_dir" "$log_dir_run"

  local runner='set -euo pipefail; export PATH="'"$BUGGY_CIRCOM_DIR"'":$PATH; test -f "'"$ARTIFICIAL_BUGS_CONFIG"'"; export CIRCOM_ARTIFICIAL_BUGS_CONFIG="'"$ARTIFICIAL_BUGS_CONFIG"'"; circom --help | grep -Fq "artificial-bugs-build"; python3 cli.py explore --tool circom -v'"$VERBOSITY"' --timeout '"$TOOL_TIMEOUT"' --working-dir '"$exp_work_dir"' --report-dir '"$prefixed_report_dir"' --seed '"$run_seed"' --config '"$config_path"''

  if [[ $USE_TMP -eq 1 ]]; then
    podman run --timeout="$PODMAN_TIMEOUT" --pids-limit=-1 --cpus="$CIRCOM_CPUS" \
      -v "$REPO_ROOT":/workspace -v "$TMP_DIR":/tmp --workdir /workspace/circuzz --rm "$IMAGE_CIRCOM_DEFAULT" \
      bash -lc "$runner" > "$log_dir_run/$run_name-explore.log" 2>&1
  else
    podman run --timeout="$PODMAN_TIMEOUT" --pids-limit=-1 --cpus="$CIRCOM_CPUS" \
      -v "$REPO_ROOT":/workspace --workdir /workspace/circuzz --rm "$IMAGE_CIRCOM_DEFAULT" \
      bash -lc "$runner" > "$log_dir_run/$run_name-explore.log" 2>&1
  fi
}

run_group() {
  local group_prefix="$1"
  local group_num="$2"
  local group_config="$3"

  if [[ "$group_num" -eq 0 ]]; then
    return
  fi

  local pids=()
  for i in $(seq 1 "$group_num"); do
    local r="$RANDOM"
    local run_name="$group_prefix-$i"
    echo "$run_name $r" >> "$OBJ_DIR/seeds.txt"
    start_one "$run_name" "$r" "$group_config" &
    pids+=($!)
    echo "Started $run_name/$group_num with seed $r ..."
    sleep "$WAIT_BETWEEN"
  done

  wait "${pids[@]}"
}

overall_status=0
pids=()
labels=()

run_group "circom-basic" "$CIRCOM_BASIC_NUM" "$CIRCOM_CONFIG_BASIC" &
pids+=($!)
labels+=("circom-basic")

run_group "circom-fully" "$CIRCOM_FULLY_NUM" "$CIRCOM_CONFIG_FULLY" &
pids+=($!)
labels+=("circom-fully")

for idx in "${!pids[@]}"; do
  if wait "${pids[$idx]}"; then
    echo "group '${labels[$idx]}' finished successfully"
  else
    echo "group '${labels[$idx]}' failed"
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
