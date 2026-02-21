# SMT Solver Experiments

This directory contains experiments that were conducted for the SMT solver part of the FYP project.

## Podman images

Build the two experiment images (Circom + Gnark):

```bash
cd smt-solver/experiments
./build_podman.sh
```

Default tags:

- `localhost/smt-exp-circom:latest`
- `localhost/smt-exp-gnark:latest`

Both images include:

- Picus runtime (`/Picus/run-picus`, symlinked as `~/Picus/run-picus`)
- `cvc5` (finite-field capable from Picus base)
- `z3`
- Python deps required by `smt-solver`

## Experiments

- `fusion/`: General fusion experiment scripts.
- `picus_fusion/`: Picus fusion experiments and configuration.
- `sat_fusion/`: SAT fusion experiments and configuration.

All three scripts are thin wrappers over shared logic in `experiments/common.sh`.
To customize a run, set env vars in the wrapper or at invocation time.

Each experiment script now runs inside Podman automatically and bind-mounts the repository at `/workspace`.
All outputs (`obj/`, `*.out`) are written back to the host filesystem under the original experiment folder.
