# SMT Solver CLI

FYP ICL

Trying to create a SMT solver that uses circom r1cs in the middle with intention of testing it later and uncovering bugs in circom.

## SMT solver
Run
```bash
chmod +x ./cli.py
./cli.py --help
``` 
to see a list of commands. The main command for the solver is `./cli.py solve`.
Run `./cli.py solve --help` for more details.~

When using circom dsl make sure your `tmp-dir` has circomlib files at ../circomlib. E.g set `--tmp-dir experiments/tmp-circom`.

## Requirements / Installation

### ZK DSLs
You have to have `go` and `circom` installed

### YinYang
`pip install yinyang`

### Z3

**Ubuntu / Debian**
```bash
sudo apt install -y z3
```

**Python bindings **
```bash
pip install z3-solver
```

### cvc5 (from source, with CoCoA backend)

See [this instructions](./CVC_COCOA.md)
