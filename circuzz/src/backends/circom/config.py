from dataclasses import dataclass

from backends.common.config_shared import GeneratorSource, OracleType, SMTFusionSettings

@dataclass(frozen=True)
class CircomConfig():
    """
    circom tool configuration
    """
    # Constraining relations. Useful for quadratic generator
    constrain_equality_assertions : bool
    constrain_sharp_inequality_assertions : bool # <, >

    # probability for boundary values
    boundary_input_probability : float

    # this value determines how often tests are executed
    test_iterations  : int

    # likelihood of the CPP witness generation (if once compiled its always used for all inputs)
    likelihood_cpp_witness_generation : float

    # likelihood of the SnarkJS witness check
    likelihood_snark_witness_check : float

    # probability to constraint an assignment "<==" instead of "<--"
    constraint_assignment_probability: float

    # probability to unwrap and constrain assertions
    unwrap_assertion_probability: float

    # Oracle type
    oracle_type : OracleType
    # Source used for generation
    generator_source: GeneratorSource
    # SMT-fusion shared settings
    smt_fusion: "SMTFusionSettings"
    # Probability of picking BN128 curve in SMT mode (BN128 enables prove/verify path).
    _smt_bn128_probability: float

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

    @property
    def smt_bn128_probability(self) -> float:
        return self._smt_bn128_probability

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> 'CircomConfig':

        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        test_iterations  = int(value.get("test_iterations", 20))
        likelihood_cpp_witness_generation = float(value.get("likelihood_cpp_witness_generation", 0.1))
        likelihood_snark_witness_check = float(value.get("likelihood_snark_witness_check", 0))
        constraint_assignment_probability = float(value.get("constraint_assignment_probability", 0.5))
        oracle_type = OracleType.from_str(value.get("oracle_type", "circuzz"))
        generator_source = GeneratorSource.from_str(value.get("generator_source", "random_ir"))
        constrain_equality_assertions = bool(value.get("constrain_equality_assertions", False))
        constrain_sharp_inequality_assertions = bool(value.get("constrain_sharp_inequality_assertions", False))
        unwrap_assertion_probability = float(value.get("unwrap_assertion_probability", 0))
        smt_fusion = SMTFusionSettings.from_dict(value)
        smt_bn128_probability = float(value.get("smt_bn128_probability", 1.0 / 7.0))
        if smt_bn128_probability < 0 or smt_bn128_probability > 1:
            raise ValueError("circom.smt_bn128_probability must be in [0, 1]")

        return CircomConfig \
            ( boundary_input_probability = boundary_input_probability
            , test_iterations = test_iterations
            , likelihood_cpp_witness_generation = likelihood_cpp_witness_generation
            , likelihood_snark_witness_check = likelihood_snark_witness_check
            , constraint_assignment_probability = constraint_assignment_probability
            , unwrap_assertion_probability = unwrap_assertion_probability
            , oracle_type = oracle_type
            , generator_source = generator_source
            , smt_fusion = smt_fusion
            , constrain_equality_assertions = constrain_equality_assertions
            , constrain_sharp_inequality_assertions = constrain_sharp_inequality_assertions
            , _smt_bn128_probability = smt_bn128_probability
            )
