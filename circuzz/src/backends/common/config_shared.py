from dataclasses import dataclass
from enum import StrEnum


class OracleType(StrEnum):
    CIRCUZZ = "circuzz"
    PICUS = "picus"
    SMT_PIPELINE = "smt_pipeline"

    @classmethod
    def from_str(cls, value: str) -> "OracleType":
        match value:
            case "circuzz":
                return OracleType.CIRCUZZ
            case "picus":
                return OracleType.PICUS
            case "smt_pipeline":
                return OracleType.SMT_PIPELINE
            case _:
                raise NotImplementedError(f"unimplemented oracle type '{value}', try {list(OracleType)}")


class GeneratorSource(StrEnum):
    RANDOM_IR = "random_ir"
    SMT_FUSION = "smt_fusion"

    @classmethod
    def from_str(cls, value: str) -> "GeneratorSource":
        match value:
            case "random_ir":
                return GeneratorSource.RANDOM_IR
            case "smt_fusion":
                return GeneratorSource.SMT_FUSION
            case _:
                raise NotImplementedError(f"unimplemented generator source '{value}', try {list(GeneratorSource)}")


@dataclass(frozen=True)
class SMTFusionSettings:
    smt_solver_path: str | None
    smt_seed_dir: str | None
    smt_num_outputs: int | None
    smt_max_models: int | None
    smt_yinyang_config: str | None
    smt_oracle: str
    smt_max_attempts: int | None

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> "SMTFusionSettings":
        smt_solver_path = value.get("smt_solver_path", None)
        smt_seed_dir = value.get("smt_seed_dir", None)
        smt_num_outputs_raw = value.get("smt_num_outputs", None)
        smt_num_outputs = int(smt_num_outputs_raw) if smt_num_outputs_raw is not None else None
        smt_max_models_raw = value.get("smt_max_models", None)
        smt_max_models = int(smt_max_models_raw) if smt_max_models_raw is not None else None
        smt_yinyang_config = value.get("smt_yinyang_config", None)
        smt_oracle = str(value.get("smt_oracle", "sat"))
        smt_max_attempts_raw = value.get("smt_max_attempts", None)
        smt_max_attempts = int(smt_max_attempts_raw) if smt_max_attempts_raw is not None else None

        return SMTFusionSettings(
            smt_solver_path=smt_solver_path,
            smt_seed_dir=smt_seed_dir,
            smt_num_outputs=smt_num_outputs,
            smt_max_models=smt_max_models,
            smt_yinyang_config=smt_yinyang_config,
            smt_oracle=smt_oracle,
            smt_max_attempts=smt_max_attempts,
        )
