SCRIPT_DIR=$(dirname -- "$0")
``
cd $SCRIPT_DIR/

yinyang "python3 ../../cli.py solve --tmp-dir ./tmp_circom/" -o sat ../../benchmarks/SMT-benchmarks/core/unsat > yy_unsat.out 2>&1
