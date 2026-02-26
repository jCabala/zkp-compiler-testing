# circom-artificial-bugs

Runs the standard Circom `circuzz` pipeline while forcing the Circom compiler
binary to:

- `/workspace/smt-solver/third_party/artificial-bugs/circom/target/release/circom`

This compiler path is only injected in this experiment's `explore.sh` by prepending
`PATH` inside the container.
Both groups also use a shared artificial-bugs config file:

- `config/artificial_bugs_config.json`

passed through `CIRCOM_ARTIFICIAL_BUGS_CONFIG`.

`explore.sh` starts two Circom groups in parallel:

1. `circom-basic-*` using `config/circom.json`
2. `circom-fully-*` using `config/circom-fully.json` (mirrors the generator/setup
from `fyp_experiments/fully-constraint-circom`)

Tune instance counts in script vars:

- `CIRCOM_BASIC_NUM`
- `CIRCOM_FULLY_NUM`

## Run

```bash
cd circuzz/fyp_experiments/circom-artificial-bugs
./explore.sh
```

Results are written under:

- `circuzz/fyp_experiments/circom-artificial-bugs/obj/`
