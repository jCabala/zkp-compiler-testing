# SMT Solver CLI

FYP ICL — differential testing of ZK DSL compilers using SMT-based oracle checking and metamorphic fusion (YinYang).

## CLI

```bash
chmod +x ./cli.py
./cli.py --help
```

The main command is `./cli.py solve`. Run `./cli.py solve --help` for details.

Circom compilation uses the shared library at `third_party/circomlib`.

## Running Experiments

All experiments are driven by `experiments/run_experiments.py` with a JSON config file. Each config declares a list of *instances*, where each instance specifies the ZK DSL, oracle backend (SMT solver or Picus), benchmark directory, and YinYang fusion settings.

### Quick start

```bash
# Run a single config locally (no containers)
python experiments/run_experiments.py --config experiments/configs/circom_exp_config.json --local

# Run with podman containers (default when not inside a container)
python experiments/run_experiments.py --config experiments/configs/circom_exp_config.json

# Run only one named instance from a config
python experiments/run_experiments.py --config experiments/configs/circom_exp_config.json --instance-name sat_circom_ff --local
```

Results are written to `experiments/results/<instance_name>.json` plus a `summary.json`.

### Config files

All configs live under `experiments/configs/`:

| Config | DSL | Description |
|---|---|---|
| `circom_exp_config.json` | Circom | SAT / UNSAT / Picus on `benchmarks/prod/` |
| `circom_poseidon_config.json` | Circom | Poseidon-specific benchmarks |
| `gnark_exp_config.json` | Gnark (Go) | SAT + Picus on gnark benchmarks |
| `noir_exp_config.json` | Noir | SAT / UNSAT / Picus on `benchmarks/prod/` |
| `zokrates_exp_config.json` | ZoKrates | SAT / UNSAT / Picus, with and without `circ` backend |
| `cvc5_exp_config.json` | SMT2 (direct) | Direct cvc5 testing (`gb` vs `split` FF solver) |
| `artbugs_bool.json` | Circom | Artificial-bug injection on boolean benchmarks |
| `artbugs_ff.json` | Circom | Artificial-bug injection on finite-field benchmarks |

### Oracle backends

- **`smt`** — wraps `./cli.py solve` (compiles DSL → R1CS/ACIR → SMT2, then calls cvc5 or z3).
- **`picus`** — wraps `./cli.py solve` with the Picus uniqueness checker as the oracle.
- **`direct`** — calls the solver binary directly on `.smt2` files (no DSL compilation step; used by `cvc5_exp_config.json`).

### Benchmark directories

| Path | Contents |
|---|---|
| `benchmarks/prod/sat` | Finite-field SAT seeds |
| `benchmarks/prod/unsat` | Finite-field UNSAT seeds |
| `benchmarks/prod/unique` | Finite-field uniqueness seeds (for Picus) |
| `benchmarks/core/sat` | Boolean SAT seeds |
| `benchmarks/core/unsat` | Boolean UNSAT seeds |
| `benchmarks/core/unique-simple` | Boolean uniqueness seeds |

### Podman containers

Container images are built once with:

```bash
bash experiments/podman/build_podman.sh
```

This builds four images (one per DSL): `smt-exp-circom`, `smt-exp-gnark`, `smt-exp-noir`, `smt-exp-zokrates`. Override image names via environment variables `IMAGE_CIRCOM`, `IMAGE_GNARK`, `IMAGE_NOIR`, `IMAGE_ZOKRATES`. Memory limits default to 64 GB; override with `CONTAINER_MEMORY`.

When `run_experiments.py` is invoked without `--local` (and outside a container), it automatically launches one podman container per instance in parallel.

## Requirements / Installation

### ZK DSLs

- **Circom**: install `circom` from source or via npm
- **Gnark**: requires `go` (≥ 1.21)
- **Noir**: install `nargo`
- **ZoKrates**: install `zokrates`

### Python dependencies

```bash
pip install -r requirements.txt
```

### YinYang

```bash
pip install yinyang
```

### Z3

**Ubuntu / Debian**

```bash
sudo apt install -y z3
pip install z3-solver
```

### cvc5 (from source, with CoCoA backend)

See [CVC_COCOA.md](./CVC_COCOA.md)

### Picus

This tool assumes a runPicus script is at `~/Picus/runPicus`. For the installation guide see [Veridise/Picus](https://github.com/Veridise/Picus).

## Running Tests

```bash
python -m pytest tests/ -v
# or a single file:
python -m pytest tests/test_prune.py -v
```
