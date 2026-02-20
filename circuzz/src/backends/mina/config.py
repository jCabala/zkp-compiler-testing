from dataclasses import dataclass


@dataclass(frozen=True)
class MinaConfig:
    """
    Mina/o1js tool configuration.
    """

    # Probability to choose boundary values for inputs
    boundary_input_probability: float

    # How many inputs are executed on the circuits
    test_iterations: int

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> 'MinaConfig':
        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        test_iterations = int(value.get("test_iterations", 5))
        return MinaConfig(
            boundary_input_probability=boundary_input_probability,
            test_iterations=test_iterations,
        )
