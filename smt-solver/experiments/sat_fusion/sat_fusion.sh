#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
source "$SCRIPT_DIR/../common.sh"

ORACLE="sat" # sat or unsat
BENCHMARKS="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/sat/"
TIMEOUT="30" # seconds
SOLVER="picus" # z3 or cvc5 or picus
PRUNE="2"
DSL="circom" # gnark or circom
CONFIG="./sat_fusion_config.txt"
PRUNE_SEED="42"

CLI_COMMAND="python3.11 /workspace/smt-solver/cli.py solve --zk-dsl $DSL --solver $SOLVER --prune $PRUNE --prune-seed $PRUNE_SEED --tmp-dir /workspace/smt-solver/experiments/tmp_fusion/"
YY_CONFIG="$CONFIG"
OUT_FILE="./obj/sat_fusion.out"

run_in_podman_if_needed "sat_fusion/sat_fusion.sh"
cd "$SCRIPT_DIR"
run_yinyang_experiment
