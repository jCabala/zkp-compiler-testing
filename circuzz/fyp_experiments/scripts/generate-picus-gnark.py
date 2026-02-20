#!/usr/bin/env python3
"""
Script to generate programs using the quadratic generator and store Gnark versions.
"""

import sys
import os
from pathlib import Path
from random import Random

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from backends.gnark.emitter import EmitVisitor
from backends.gnark.ir2gnark import IR2GnarkVisitor
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
            "generator": GeneratorKind.QUADRATIC,
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


def generate_program(seed: int, config: IRConfig):
    """
    Generate a single program using the quadratic generator.
    
    Args:
        seed: Random seed for reproducibility
        config: IR configuration
        
    Returns:
        tuple: (circuit_ir, gnark_code)
    """
    # Generate the IR circuit
    circuit = generate_random_circuit(CurvePrime.BN128, False, config, seed)
    
    # Transform to Gnark
    gnark_ast = IR2GnarkVisitor().transform(circuit)

    # Emit Gnark code
    emitter = EmitVisitor(add_picus_annotations=True)
    gnark_code = emitter.emit(gnark_ast)
    
    return circuit, gnark_code


def main():
    """Main function to generate multiple programs and save them."""
    # Configuration
    num_programs = 10  # Number of programs to generate
    base_seed = 42  # Starting seed
    output_dir = Path(__file__).parent / "programs"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create configuration
    config = create_config()
    
    print(f"Generating {num_programs} programs using the quadratic generator...")
    print(f"Output directory: {output_dir}")
    print()
    
    # Generate programs
    rng = Random(base_seed)
    num_success = 0
    for i in range(num_programs):
        seed = rng.randint(1000000, 9999999)
        
        try:
            # Generate the program
            _, gnark_code = generate_program(seed, config)
            
            # Save the Gnark code
            output_file = output_dir / f"circuit_{seed}.go"
            output_file.write_text(gnark_code)
            
            print(f"[{i+1:2d}/{num_programs}] Generated: {output_file.name} (seed: {seed})")
            num_success += 1
            
        except Exception as e:
            print(f"[{i+1:2d}/{num_programs}] Error generating program with seed {seed}: {e}")
            continue
    
    print()
    print(f"Successfully generated {num_success}/{num_programs} programs in {output_dir}")
    print()


if __name__ == "__main__":
    main()
