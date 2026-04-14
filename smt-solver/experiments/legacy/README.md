# SMT Solver Experiments

This directory contains experiments that were conducted for the SMT solver part of the FYP project.

## Experiments Overview

- `picus_fusion/`: Picus fusion experiments and configuration.
- `sat_fusion/`: SAT fusion experiments and configuration.
- `circom-artificial-bugs/`: Using fusion to test a circom compiler containing artificial bugs.

Each experiment is configurable. For example you can configure the solver and benchmarks you are using, pruning level and seeds.

## Sample Data

The `data/` folder stores a curated snapshot of generated program artifacts for both `sat` and `picus` fusion experiments for both `circom` and `gnark`.

### SAT Fusion

#### Generator:

Use semantic fusion on bool-only programs with `xor` as the fusion function. Treat fused variables as outputs and the rest as inputs.

#### Oracle:

Use SMT solver on R1CS to see if itpreserves SAT.

### Picus Fusion

#### Generator:

Use semantic fusion with UNIQUE-SAT benchmarks & "determinism optimisation": when we fuse variables `x` and `y` to get `z`, we replece ALL occurences of one variable with inverse fusion on no occurences of other. If using benchmarks with unique solutions (UNIQUE-SAT) this fusion guarantees properly constrained programs.

#### Oracle:

Run `picus` on R1CS to see if it is properly constrained.

### Circom Artificial Bugs

In this experiment we introduce multiple soundness and completeness bugs to constraint generation in the circom compiler to test the bug finding capabilities of fusion. The possible bugs (configurable in [here](./circom-artificial-bugs/artificial_bugs_config.json)) are: always empty r1cs, remove vvariables at random, remove constraints at random, change random constants & perturbe random constants (add +-1, +-2 or +-3)

## Podman images

All experiments run on podman images. Build the two experiment images (Circom + Gnark):

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
