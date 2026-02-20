"""
All functions and classes related to using the PICUS based oracle
"""

from enum import StrEnum
from circuzz.common.colorlogs import get_color_logger
from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from circuzz.ir.config import IRConfig
from circuzz.ir.nodes import Circuit
from .ir2circom import IR2CircomVisitor
from .emitter import EmitConfig, EmitVisitor
from random import Random
import tempfile
from pathlib import Path
import subprocess  

logger = get_color_logger()

PICUS_COMMAND = "/Picus/run-picus"  # Path to the PICUS executable

class ConstraintLevel(StrEnum):
    FULLY_CONSTRAINED = "fully_constrained"
    UNDER_CONSTRAINED = "under_constrained"
    INCONCLUSIVE = "inconclusive"

class PICUSCheckResult:
    def __init__(self, constraint_level: ConstraintLevel):
        self.constraint_level = constraint_level

def ir_to_circom_ast(
    circuit: Circuit,
) -> object:
    """Convert an IR `Circuit` to Circom AST (Document)."""
    constraint_assignment_probability = 1 # We want all constraints to be assigned
    rng = Random() # Rng is only used for random assignments, which we don't need here.

    visitor = IR2CircomVisitor(
        constraint_assignment_probability=constraint_assignment_probability,
        rng=rng,
    )
    return visitor.transform(circuit)

def ir_to_circom_code(
    circuit: Circuit,
    emit_config: EmitConfig,
) -> str:
    """Convert an IR `Circuit` to Circom source code string."""
    circom_ast = ir_to_circom_ast(
        circuit,
    )
    emitter = EmitVisitor(emit_config)
    return emitter.emit(circom_ast)

def run_picus_check(circom_code: str) -> PICUSCheckResult:
    logger.info("Running PICUS constraint check...")
    # Save circuit to a temporary file
    with tempfile.TemporaryDirectory() as tmpdirname:
        circuit_path = Path(tmpdirname) / "circuit.circom"
        with open(circuit_path, 'w') as f:
            f.write(circom_code)

        # Run picus check command
        result = subprocess.run(
            [PICUS_COMMAND, str(circuit_path)],
            capture_output=True,
            text=True,
        )

        if "The circuit is properly constrained" in result.stdout:
            logger.info("PICUS result: Fully constrained")
            return PICUSCheckResult(ConstraintLevel.FULLY_CONSTRAINED)
        elif "The circuit is underconstrained" in result.stdout:
            logger.info("PICUS result: Under constrained")
            return PICUSCheckResult(ConstraintLevel.UNDER_CONSTRAINED)
        else:
            logger.info("PICUS result: Inconclusive")
            return PICUSCheckResult(ConstraintLevel.INCONCLUSIVE)

def is_properly_constrained(circom_code: str) -> bool:
    return run_picus_check(circom_code).constraint_level == ConstraintLevel.FULLY_CONSTRAINED

def generate_picus_constrained_circom_code \
    ( curve: CurvePrime
    , exclude_prime: bool
    , config: IRConfig
    , seed: int
    , emit_config: EmitConfig
    ) -> tuple[Circuit, str, int]:
    """
    Uses normal random circuit generation but ensures the circuit is
    properly constrained for use with the PICUS oracle.

    It also returns the number of tries it took to generate such a circuit.
    """

    circom_code = None
    circuit = None
    num_tries = 0
    while not circuit or not is_properly_constrained(circom_code):
        circuit = generate_random_circuit(curve, exclude_prime, config, seed)
        circom_code = ir_to_circom_code(circuit, emit_config=emit_config)
        seed += 1  # Change seed to get a different circuit next time if needed.
        num_tries += 1

    return circuit, circom_code, num_tries