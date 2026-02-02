SCRIPT_DIR=$(dirname -- "$0")
cd $SCRIPT_DIR/

## CONFIGURATION
ORACLE=sat # sat or unsat
BENCHMARKS=$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/sat/
TIMEOUT=30 # seconds
SOLVER="z3" # z3 or cvc5
DSL="circom" # gnark or circom
CONFIG="./sat_fusion_config.txt"

# If object directory does not exist, create it
if [ ! -d ./obj ]; then
    mkdir ./obj
fi

CLI_COMMAND="../../cli.py solve --solver $SOLVER --tmp-dir ../tmp_fusion/"
yinyang "$CLI_COMMAND" --oracle $ORACLE --timeout $TIMEOUT -c $CONFIG --l ./obj/logs --s ./obj/scratch --b ./obj/bugs $BENCHMARKS > sat_fusion.out 2>&1