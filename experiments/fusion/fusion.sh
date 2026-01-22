SCRIPT_DIR=$(dirname -- "$0")
cd $SCRIPT_DIR/

## CONFIGURATION
ORACLE=sat # sat or unsat
TIMEOUT=300 # seconds
BENCHMARKS=$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/sat/
SOLVER="z3" # z3 or cvc5
DSL="gnark" # gnark or circom
# Uncomment the next line to enable boolean-only mode if you are solving only boolean (core theory) benchmarks. Temporary solution. For cvc5 it doesn't really matter but huge help for z3.
#BOOL_ONLY=--bool-only

# If object directory does not exist, create it
if [ ! -d ./obj ]; then
    mkdir ./obj
fi

yinyang "../../cli.py solve $BOOL_ONLY --solver $SOLVER --tmp-dir ../tmp_fusion/"  --oracle $ORACLE --timeout $TIMEOUT --l ./obj/logs --s ./obj/scratch --b ./obj/bugs $BENCHMARKS > fusion.out 2>&1