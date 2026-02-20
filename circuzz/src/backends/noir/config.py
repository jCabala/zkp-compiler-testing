from dataclasses import dataclass

from backends.common.config_shared import GeneratorSource, OracleType, SMTFusionSettings

@dataclass(frozen=True)
class NoirConfig():
    """
    noir tool configuration
    """

    # Oracle type
    oracle_type: OracleType
    # Source used for generation
    generator_source: GeneratorSource

    # probability to chose boundary values for inputs
    boundary_input_probability : float

    # this value determines how often tests are executed
    test_iterations  : int
    # in smt_pipeline mode, stop after witness generation (skip bb prove/verify)
    smt_witness_only: bool
    # SMT-fusion shared settings
    smt_fusion: SMTFusionSettings

    @property
    def smt_solver_path(self) -> str | None:
        return self.smt_fusion.smt_solver_path

    @property
    def smt_seed_dir(self) -> str | None:
        return self.smt_fusion.smt_seed_dir

    @property
    def smt_num_outputs(self) -> int | None:
        return self.smt_fusion.smt_num_outputs

    @property
    def smt_max_models(self) -> int | None:
        return self.smt_fusion.smt_max_models

    @property
    def smt_yinyang_config(self) -> str | None:
        return self.smt_fusion.smt_yinyang_config

    @property
    def smt_oracle(self) -> str:
        return self.smt_fusion.smt_oracle

    @property
    def smt_max_attempts(self) -> int | None:
        return self.smt_fusion.smt_max_attempts

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> 'NoirConfig':
        oracle_type = OracleType.from_str(value.get("oracle_type", "circuzz"))
        generator_source = GeneratorSource.from_str(value.get("generator_source", "random_ir"))
        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        test_iterations  = int(value.get("test_iterations", 5))
        smt_witness_only_raw = value.get("smt_witness_only", False)
        if isinstance(smt_witness_only_raw, str):
            smt_witness_only = smt_witness_only_raw.lower() in ("1", "true", "yes", "on")
        else:
            smt_witness_only = bool(smt_witness_only_raw)
        smt_fusion = SMTFusionSettings.from_dict(value)
        return NoirConfig \
          ( oracle_type = oracle_type
          , generator_source = generator_source
          , boundary_input_probability = boundary_input_probability
          , test_iterations = test_iterations
          , smt_witness_only = smt_witness_only
          , smt_fusion = smt_fusion
          )
