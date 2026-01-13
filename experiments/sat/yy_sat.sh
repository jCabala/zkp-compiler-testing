SCRIPT_DIR=$(dirname -- "$0")

cd $SCRIPT_DIR/

yinyang "python3 ../../cli.py solve --tmp-dir ./tmp_circom/" -o sat ../../benchmarks/SMT-benchmarks/core/sat > yy_sat.out 2>&1
