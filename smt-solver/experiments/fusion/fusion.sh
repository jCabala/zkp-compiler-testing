#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
source "$SCRIPT_DIR/../common.sh"

ORACLE="sat" # sat or unsat
TIMEOUT="300" # seconds
BENCHMARKS="$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/lia/sat/"
SOLVER="z3" # z3 or cvc5
DSL="gnark" # gnark or circom
BOOL_ONLY="" # e.g. --bool-only
TMP_DIR="${TMP_DIR:-/workspace/smt-solver/experiments/tmp_fusion}"

CLI_COMMAND="python3 /workspace/smt-solver/cli.py solve --zk-dsl $DSL $BOOL_ONLY --solver $SOLVER --tmp-dir $TMP_DIR"
OUT_FILE="./obj/fusion.out"

run_in_podman_if_needed "fusion/fusion.sh"
cd "$SCRIPT_DIR"
run_yinyang_experiment
