# SMT Fusion Pipeline Experiment

This experiment runs Circuzz in `smt_pipeline` oracle mode for:

- `circom`
- `gnark`
- `noir`

Generation is delegated to sibling repo `../smt-solver` via:

- `fuse-smt-to-dsl`
- `--format circuzz`

Each backend replays SMT models as witness inputs and treats any stage failure as a violation.

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
