SCRIPT_DIR=$(dirname -- "$0")
cd $SCRIPT_DIR/

opfuzz "python3 ../../cli.py solve --tmp-dir ./tmp_circom/;z3" ../../benchmarks/SMT-benchmarks/core/sat/ > of.out 2>&1