# SMT Fusion Pipeline Experiment

This experiment runs Circuzz in `smt_pipeline` oracle mode for:

- `circom`
- `gnark`
- `noir`

Generation is delegated to sibling repo `../smt-solver` via:

- `fuse-smt-to-dsl`
- `--format circuzz`

Each backend replays SMT models as witness inputs and treats any stage failure as a violation.

`smt_prove_verify_probability` can be set per backend in `[0,1]`:
- `0.0`: always stop after witness generation
- `1.0`: always run prove/verify
- in between: run prove/verify probabilistically per replayed model

## How to run

```bash
cd fyp_experiments/smt-fusion
./build_podman.sh
./explore.sh
```

Run a subset of DSL/tool backends:

```bash
./explore.sh circom noir
```

Supported selectors:

- `circom`
- `gnark`
- `noir`
