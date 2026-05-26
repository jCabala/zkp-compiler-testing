# Experiments

Each experiment has an `explore.sh` and (where needed) a `build_podman.sh` script. Build the podman images once, then run experiments with the exploration script. All logs and intermediary data are stored under `<experiment-name>/obj/<run-name>`.

## Experiments

### smt-fusion

Uses the `smt-solver` code to generate programs together with models for the variables that should satisfy witness generation by construction. Then runs the circuzz oracle on the program and expects all stages to pass. For witness generation it uses the generated models. Currently supports: `circom`, `gnark`, and `noir` (in `noir` prove and verify steps are not supported).

```bash
cd fyp_experiments/smt-fusion
./build_podman.sh
./explore.sh            # all backends
./explore.sh circom noir  # subset
```

### circom-artificial-bugs

Runs Circom with the default circuzz pipeline but forces the compiler binary to the artificial-bugs build from sibling `smt-solver` (`third_party/artificial-bugs/circom/target/release/circom`). Starts two groups in parallel: `circom-basic-*` and `circom-fully-*`.

```bash
cd fyp_experiments/circom-artificial-bugs
./explore.sh
```

### mina

Runs circuzz on the `mina` backend.

```bash
cd fyp_experiments/mina
./build_podman.sh
./explore.sh
```

### fully-constraint-circom

The original `circom` generator only added asserts to programs. This experiment uses a generator that tries to fully constrain as many outputs as possible.

```bash
cd fyp_experiments/fully-constraint-circom
./build_podman.sh
./explore.sh
```

### circom-picus & gnark-picus

`picus` is a tool for detecting under-constrained inputs. These experiments use it as a metamorphic oracle instead of the standard circuzz oracle.

```bash
cd fyp_experiments/circom-picus   # or gnark-picus
./experiments.sh
```

### quadratic-circuzz

Uses normal `circuzz` oracles but with the `quadratic` generator, which generates programs with constraints of the form `A * B = C`.

```bash
cd fyp_experiments/quadratic-circuzz
./build_podman.sh
./explore.sh
```

### zokrates

Runs circuzz on the `zokrates` backend with arithmetic and boolean generator configs.

```bash
cd fyp_experiments/zokrates
./build_podman.sh
./explore.sh
```

### artificial-bugs

Shared configs (`standard.json`, `standard-bool.json`, `picus.json`) used by other experiments that inject artificial bugs into the compiler under test.

### o1js-overhead

Runs the standard circuzz oracle on `circom`, `gnark`, and `mina` backends to measure overhead. Uses configs under `configs/`.

### weak-sat

Runs circuzz on `circom` and `gnark` with rewrite-only metamorphic testing (weakening rules disabled, `weakening_probability: 0`). Useful for isolating equivalence-rewriting bugs from weakening-related ones.
