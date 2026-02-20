from dataclasses import dataclass

from backends.common.config_shared import GeneratorSource, OracleType, SMTFusionSettings

@dataclass(frozen=True)
class GnarkConfig():
    """
    gnark tool configuration
    """

    # Use picus oracle
    oracle_type: OracleType
    # Source used for generation
    generator_source: GeneratorSource

    # amount of different circuits tested at the same time (should be >= 1)
    bundle_size : int

    # probability to chose boundary values as input values
    boundary_input_probability : float

    # how many inputs are executed on the circuits
    test_iterations : int

    # string which is provided for go test -timeout
    go_test_timeout : str | None
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
    def from_dict(cls, value: dict[str, str]) -> 'GnarkConfig':
        bundle_size = int(value.get("bundle_size", 5))
        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        test_iterations = int(value.get("test_iterations", 1))
        go_test_timeout = value.get("go_test_timeout", None)
        oracle_type = OracleType.from_str(value.get("oracle_type", "circuzz"))
        generator_source = GeneratorSource.from_str(value.get("generator_source", "random_ir"))
        smt_fusion = SMTFusionSettings.from_dict(value)

        return GnarkConfig \
            ( bundle_size = bundle_size
            , boundary_input_probability = boundary_input_probability
            , test_iterations = test_iterations
            , go_test_timeout = go_test_timeout
            , oracle_type = oracle_type
            , generator_source = generator_source
            , smt_fusion = smt_fusion
            )
