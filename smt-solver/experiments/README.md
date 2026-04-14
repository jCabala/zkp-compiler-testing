# Experiments

This folder contains the experiment runner, configs, and legacy experiment assets.

## Configs
Configs live under `experiments/configs/` and are consumed by `run_experiments.py`.

Example:

```bash
python3 experiments/run_experiments.py --config experiments/configs/bool_exp_config.json
python3 experiments/run_experiments.py --config experiments/configs/ff_exp_config.json
```

By default, the runner launches each configured experiment in its own podman
container, using the DSL-specific images from `IMAGE_CIRCOM` / `IMAGE_GNARK`.
Each instance is executed through Yinyang, with artifacts written under
`experiments/obj/`:

- `experiments/obj/<instance>.out`
- `experiments/obj/<instance>/{logs,scratch,bugs}`
- `experiments/obj/<instance>/solve_config.json`
- `experiments/obj/run_config_<timestamp>_<instance>.env`

Use `--local` to run directly on the host instead.

## Legacy
Older experiment assets are stored in `experiments/legacy/`.

## Podman
Podman-related scripts are stored in `experiments/podman/`.
