from pathlib import Path
from typing import Protocol

from cross_oracle.generation.types import SMTFusionProgram, SMTFusionRunConfig


class FusionGeneratorBackend(Protocol):
    def generate(
        self,
        working_dir: Path,
        config: SMTFusionRunConfig,
        seed: int | None = None,
    ) -> list[SMTFusionProgram]:
        ...
