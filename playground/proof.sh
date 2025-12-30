SCRIPT_DIR=$(dirname "$0")
CUR_DIR=$(pwd)
cd "$SCRIPT_DIR/.."

python3 cli.py generate-proof ./data/example.circom ./data/input.json -o $SCRIPT_DIR/proof

cd "$CUR_DIR"


