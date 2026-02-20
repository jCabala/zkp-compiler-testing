#!/usr/bin/env python3
"""
Script to generate programs using the quadratic generator and store Circom versions.
"""

import sys
import os
from pathlib import Path
from random import Random

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from backends.circom.lib_path_resolver import LibPathMode
from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from backends.circom.emitter import EmitConfig, EmitVisitor
from backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from circuzz.ir.config import GeneratorKind, IRConfig

def create_config():
    """Create the configuration for the quadratic generator."""
    return IRConfig.from_dict({
        "rewrite": {
            "weakening_probability": 0,
            "min_rewrites": 0,
            "max_rewrites": 0,
            "rules": {
                "equivalence": [],
                "weakening": []
            }
        },
        "generation": {
            "generator": GeneratorKind.ARITHMETIC,
            "quadratic_generator_inequality_assertion_probability": 1,

            "constant_probability_weight": 1,
            "variable_probability_weight": 1,
            "unary_probability_weight": 1,
            "binary_probability_weight": 1,
            "relation_probability_weight": 1,
            "ternary_probability_weight": 1,

            "max_expression_depth": 2,
            "min_number_of_assertions": 1,
            "max_number_of_assertions": 3,
            "min_number_of_input_variables": 2,
            "max_number_of_input_variables": 5,
            "min_number_of_output_variables": 1,
            "max_number_of_output_variables": 3,

            "max_exponent_value": 4,
            "boundary_value_probability": 0.25
        },
        "operators": {
            "relations": ["<", ">", "<=", ">=", "==", "!="],
            "boolean_unary_operators": ["!"],
            "boolean_binary_operators": ["&&", "||", "^^"],
            "arithmetic_unary_operators": ["-"],
            "arithmetic_binary_operators": ["+", "-", "*", "/", "^", "&", "|"],

            "is_arithmetic_ternary_supported": True,
            "is_boolean_ternary_supported": True
        }
    })


def generate_program(seed: int, config: IRConfig, constraint_probability: float = 0.7):
    """
    Generate a single program using the quadratic generator.
    
    Args:
        seed: Random seed for reproducibility
        config: IR configuration
        constraint_probability: Probability to use constraining assignment in Circom
        
    Returns:
        tuple: (circuit_ir, circom_code)
    """
    # Generate the IR circuit
    circuit = generate_random_circuit(CurvePrime.BN128, False, config, seed)
    
    # Transform to Circom
    rng = Random(seed)
    circom_ast = IR2CircomVisitorConstrainAssertions(constraint_probability, rng, unwrap_assertion_probability=0.8).transform(circuit)

    # Emit Circom code
    emit_config = EmitConfig(constrain_equality_assertions=True, constrain_sharp_inequality_assertions=True, lib_path_mode=LibPathMode.LOCAL)
    emitter = EmitVisitor(emit_config)
    circom_code = emitter.emit(circom_ast)
    
    return circuit, circom_code


def main():
    """Main function to generate multiple programs and save them."""
    # Configuration
    num_programs = 1000  # Number of programs to generate
    base_seed = 42  # Starting seed
    output_dir = Path(__file__).parent / "programs"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create configuration
    config = create_config()
    
    # Check if circomlib is locally present else git clone it
    local_circomlib_path = Path(output_dir / "node_modules/circomlib")

    if not local_circomlib_path.exists():
        print("circomlib not found locally. Running `npm install circomlib`...")
        os.system(f"cd {output_dir} && npm install circomlib")
    else:
        print("circomlib found locally.")

    print(f"Generating {num_programs} programs using the quadratic generator...")
    print(f"Output directory: {output_dir}")
    print()
    
    # Generate programs
    rng = Random(base_seed)
    for i in range(num_programs):
        seed = rng.randint(1000000, 9999999)
        
        # Generate the program
        _, circom_code = generate_program(seed, config)
        
        # Save the Circom code
        output_file = output_dir / f"circuit_{seed}.circom"
        output_file.write_text(circom_code)
        
        print(f"[{i+1:2d}/{num_programs}] Generated: {output_file.name} (seed: {seed})")

    
    print()
    print(f"Successfully generated {num_programs} programs in {output_dir}")
    print()

    print()
    print("Running circom compiler on generated programs...")
    print()

    num_success = 0
    for circom_file in output_dir.glob("*.circom"):
        compile_command = f"circom {circom_file}"
        result = os.system(compile_command)
        if result == 0:
            print(f"Compiled successfully: {circom_file.name}")
            num_success += 1
        else:
            print(f"Compilation failed: {circom_file.name}")

    print()
    print(f"Compilation summary: {num_success}/{num_programs} programs compiled successfully.")
    print()


if __name__ == "__main__":
    main()
