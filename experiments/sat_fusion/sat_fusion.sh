SCRIPT_DIR=$(dirname -- "$0")
cd $SCRIPT_DIR/

## CONFIGURATION
ORACLE=sat # sat or unsat
BENCHMARKS=$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/sat/
TIMEOUT=30 # seconds
SOLVER="cvc5" # z3 or cvc5
PRUNE=1
DSL="gnark" # gnark or circom
CONFIG="./sat_fusion_config.txt"
PRUNE_SEED=42

# If object directory does not exist, create it
if [ ! -d ./obj ]; then
    mkdir ./obj
fi

CLI_COMMAND="../../cli.py solve --zk-dsl $DSL --solver $SOLVER --prune $PRUNE --prune-seed $PRUNE_SEED --tmp-dir ../tmp_fusion/"
yinyang "$CLI_COMMAND" --oracle $ORACLE --timeout $TIMEOUT -c $CONFIG --l ./obj/logs --s ./obj/scratch --b ./obj/bugs $BENCHMARKS > sat_fusion.out 2>&1