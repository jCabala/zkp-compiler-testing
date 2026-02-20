from pathlib import Path

from cross_oracle.adapters.base import FusionGeneratorBackend
from cross_oracle.adapters.native_smt_solver import NativeSmtSolverBackend
from cross_oracle.generation.types import SMTFusionProgram, SMTFusionRunConfig


def run_smt_fusion_generation(
    working_dir: Path,
    config: SMTFusionRunConfig,
    seed: int | None = None,
    backend: FusionGeneratorBackend | None = None,
) -> list[SMTFusionProgram]:
    resolved_backend = backend or NativeSmtSolverBackend()
    return resolved_backend.generate(working_dir, config, seed=seed)
