SCRIPT_DIR=$(dirname -- "$0")
cd $SCRIPT_DIR/
YY_ROOT="$SCRIPT_DIR/../../third_party/yinyang"

## CONFIGURATION
ORACLE=sat # sat or unsat
BENCHMARKS=$SCRIPT_DIR/../../benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/
TIMEOUT=30 # seconds
DSL="circom" # gnark or circom

# Fixed config for picus fusion
FUSION_REWRITE_POLICY="all"
FUSION_SIDE_POLICY="one"
SOLVER="picus"
CONFIG="./picus_fusion_config.txt"

# If object directory does not exist, create it
if [ ! -d ./obj ]; then
    mkdir ./obj
fi

CLI_COMMAND="../../cli.py solve --zk-dsl $DSL --solver $SOLVER --tmp-dir ../tmp_fusion/"

# Keep sat_fusion as baseline; picus_fusion is where we enforce all-occurrence rewriting.
PYTHONPATH="$YY_ROOT" \
YY_FUSION_REWRITE_POLICY="$FUSION_REWRITE_POLICY" \
YY_FUSION_SIDE_POLICY="$FUSION_SIDE_POLICY" \
    python3 "$YY_ROOT/yinyang_cli.py" "$CLI_COMMAND" --oracle $ORACLE --timeout $TIMEOUT -c $CONFIG --l ./obj/logs --s ./obj/scratch --b ./obj/bugs $BENCHMARKS > picus_fusion.out 2>&1
