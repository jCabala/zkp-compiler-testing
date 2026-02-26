# Experiments

Each experiment has a `explore.py` and `build_podman.py` scripts. You need to buildpodman images once and then you run experiments with the exploration script. All of the ogs and intermediary data will be stored in `<experiment-name>/obj/<run-name>`.

## Current experiemtns

Here I list experimetns that are still running.

### smt-fusion

Uses the `smt-solver` code to generate programs together with models for the variables that should satisfy the witness generation by construction. Then it runs the circuzz oracle on this program and expects all stages to pass. For witness generation it uses the generated models. Currently supports: `circom`, `gnark` and `noir` (in `noir` we don't support the prove and verify steps).

### circom-artificial-bugs

Runs Circom with the default circuzz setup (basic oracle + random IR generator)
but forces the compiler binary to the artificial-bugs build from sibling
`smt-solver`.

### mina

Runs circuzz on the new `mina` backend.

## Legacy experiments

Here I list experiments that I run extensively already and am not planning to run anymore.

### fully-constrained-circom

Origianl `circom` genrator was just adding asserts to programs. This experiment uses a new generator that tries to constrain as much as it can.

### circom-picus & `gnark-picus1

`picus` is a tool allowing to detect underconstraint inputs. This experiments tries to use it as a metamorphic oracle instead of normal `circuzz` oracles.

### quadratic-circom

Using normal `circuzz` oracles but with the `quadratic` generator (generates programs that with cosntraitns of form `A * B = C` )
