# Experiments

## circom-picus

### Overview

`picus` is a tool allowing to detect underconstraint inputs. This experiments tries to use it as a metamorphic oracle instead of normal `circuzz` oracles. It also uses the `quadratic` generator.

### How to run

```bash
cd fyp_experiments/circom-picus
chmod +x ./experiments.sh

./experiment.sh
```

The report together with logs will be stored under `circom-picus/obj` directory.
You can modify the duration of the experiment in the `expderiments.sh` file.
The logs will contain all of the generated circuits.

## quadratic-circom

### Overview

Using normal `circuzz` oracles but with the `quadratic` generator.

### How to run

```bash
cd fyp_experiments/quadratic-circuzz
./build_podman.sh # Build the images
./explore.sh
```

## smt-fusion

### Overview

Runs `smt_pipeline` oracle mode for Circom/Gnark/Noir using sibling `smt-solver`
(`fuse-smt-to-dsl --format circuzz`) and model-replay based stage checks.

### How to run

```bash
cd fyp_experiments/smt-fusion
./build_podman.sh
./explore.sh
```

Run selected DSLs only:

```bash
./explore.sh circom noir
```

## Scripts

This directory contains some additionall helpful scripts.

### generate-quadratic-circom.py

Generates couple circom programs using the quadratic generator.

# Changelog

1. Added a picus oracle to circom. It can be enabled using `circom: {oracle: "picus"}` in config file.

2. Developed a `circom-picus` experiment

3. Created [quadratic ir generator](../src/circuzz/ir/generators/quadratic.py). Can be enabled in the config by using `{generation: {generator: "quadratic"}}`

4. Added a `cosntrain-equallity-assertions` flag to circom config (`circom: {constrain_equallity_assertions: true}`) that whenever we have a assertion with expression where the op is eq it (e.g `assert(a == 2)`), it will translate it into constraints (`a === 2`). For good performance you need to ensure the cosntraints will remain quadratic (e.g quadratic ir generator)

5. Added `constrain-sharp-inequallity-assertions` flag that uses `LessThan` and `GreaterThan` from circomlib to constrain circuits.

6. Added `quadratic_generator_inequality_assertion_probability` field in the `generator` config. It is used by quadratic generator to assert how often to use `<` and `>` over `===`.

7. Added a picus oracle to gnark and implemented `gnark-picus` experiments

8. Added `Mina` backend

9. Created a backend for circom that unwraps asssertions and constrains everything (apart from arithmetic `and` and `or`)

10. Added zokrates backend

11. Setup fully-constrained-circom experiments
