from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SMTFusionRunConfig:
    smt_solver_path: str
    smt_seed_dir: str
    dsl: str
    num_outputs: int
    max_models: int
    yinyang_config: str | None
    oracle: str
    max_attempts: int | None


@dataclass(frozen=True)
class SMTFusionProgram:
    name: str
    dsl_path: Path
    solution_path: Path
    models: list[dict[str, int | bool]]
