#!/usr/bin/env python3
"""
Script to generate programs using arithmetic and boolean generators and test Mina/o1js compilation.

Usage:
    python generate-mina.py              # Generate and type-check
    python generate-mina.py --no-check   # Generate only, skip type-checking
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from random import Random

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from circuzz.ir.config import GeneratorKind, IRConfig
from backends.mina.ir2mina import IR2MinaVisitor
from backends.mina.emitter import EmitVisitor


def create_arithmetic_config():
    """Create the configuration for the arithmetic generator."""
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
            "relations": ["==", "!="],
            "boolean_unary_operators": ["!"],
            "boolean_binary_operators": ["&&", "||"],
            "arithmetic_unary_operators": ["-"],
            "arithmetic_binary_operators": ["+", "-", "*", "/"],

            "is_arithmetic_ternary_supported": True,
            "is_boolean_ternary_supported": False
        }
    })


def create_boolean_config():
    """Create the configuration for the boolean generator."""
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
            "generator": GeneratorKind.BOOLEAN,

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
            "relations": ["==", "!="],
            "boolean_unary_operators": ["!"],
            "boolean_binary_operators": ["&&", "||"],
            "arithmetic_unary_operators": ["-"],
            "arithmetic_binary_operators": ["+", "-", "*", "/"],

            "is_arithmetic_ternary_supported": False,
            "is_boolean_ternary_supported": True
        }
    })



def generate_program(seed: int, config: IRConfig, is_boolean_circuit: bool = False):
    """
    Generate a single program using the specified generator.
    
    Args:
        seed: Random seed for reproducibility
        config: IR configuration specifying the generator type
        is_boolean_circuit: Whether this is a boolean circuit (all inputs/outputs are Bool)
        
    Returns:
        tuple: (circuit_ir, mina_code)
    """
    # Generate the IR circuit
    circuit = generate_random_circuit(CurvePrime.BN254, False, config, seed)
    
    # Transform to Mina/o1js AST
    mina_ast = IR2MinaVisitor(CurvePrime.BN254, is_boolean_circuit=is_boolean_circuit).transform(circuit)
    
    # Emit Mina/o1js TypeScript code
    mina_code = EmitVisitor().emit(mina_ast)
    
    return circuit, mina_code


def main():
    """Main function to generate multiple programs and test compilation."""
    parser = argparse.ArgumentParser(description="Generate Mina/o1js circuits from IR")
    parser.add_argument("--no-check", action="store_true", help="Skip TypeScript type-checking")
    parser.add_argument("-n", "--num-programs", type=int, default=5, help="Number of programs per generator (default: 5)")
    args = parser.parse_args()
    
    # Configuration
    num_arithmetic_programs = args.num_programs
    num_boolean_programs = args.num_programs
    base_seed = 42               # Starting seed
    output_dir = Path(__file__).parent / "programs-mina"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create configurations for both generators
    arithmetic_config = create_arithmetic_config()
    boolean_config = create_boolean_config()
    
    # Check if o1js is installed (skip for now - too slow in testing)
    print("Skipping o1js installation check (run 'npm install o1js' manually in output dir)")
    # result = subprocess.run(
    #     ["npm", "list", "o1js"],
    #     cwd=output_dir,
    #     capture_output=True,
    #     text=True
    # )
    # 
    # if result.returncode != 0:
    #     print("o1js not found. Running `npm install o1js`...")
    #     subprocess.run(["npm", "install", "o1js"], cwd=output_dir, check=False)
    # else:
    #     print("o1js found locally.")
    
    print()
    print(f"Generating {num_arithmetic_programs} arithmetic and {num_boolean_programs} boolean programs...")
    print(f"Output directory: {output_dir}")
    print()
    
    # Generate programs
    rng = Random(base_seed)
    generated_files = []
    total_programs = num_arithmetic_programs + num_boolean_programs
    program_count = 0
    
    # Generate arithmetic programs
    print("=" * 60)
    print("Arithmetic Generator")
    print("=" * 60)
    for i in range(num_arithmetic_programs):
        seed = rng.randint(1000000, 9999999)
        program_count += 1
        
        try:
            # Generate the program
            circuit_ir, mina_code = generate_program(seed, arithmetic_config)
            
            # Save the Mina code
            output_file = output_dir / f"arithmetic_circuit_{seed}.ts"
            output_file.write_text(mina_code)
            
            print(f"[{program_count:2d}/{total_programs}] Generated arithmetic circuit_{seed} (seed: {seed})")
            print(f"                    Inputs: {len(circuit_ir.inputs)}, "
                  f"Outputs: {len(circuit_ir.outputs)}, "
                  f"Assignments: {len(circuit_ir.assignments())}")
            
            generated_files.append(output_file)
            
        except Exception as e:
            print(f"[{program_count:2d}/{total_programs}] Error generating program with seed {seed}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print()
    
    # Generate boolean programs
    print("=" * 60)
    print("Boolean Generator")
    print("=" * 60)
    for i in range(num_boolean_programs):
        seed = rng.randint(1000000, 9999999)
        program_count += 1
        
        try:
            # Generate the program
            circuit_ir, mina_code = generate_program(seed, boolean_config, is_boolean_circuit=True)
            
            # Save the Mina code
            output_file = output_dir / f"boolean_circuit_{seed}.ts"
            output_file.write_text(mina_code)
            
            print(f"[{program_count:2d}/{total_programs}] Generated boolean circuit_{seed} (seed: {seed})")
            print(f"                  Inputs: {len(circuit_ir.inputs)}, "
                  f"Outputs: {len(circuit_ir.outputs)}, "
                  f"Assignments: {len(circuit_ir.assignments())}")
            
            generated_files.append(output_file)
            
        except Exception as e:
            print(f"[{program_count:2d}/{total_programs}] Error generating program with seed {seed}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print()
    print(f"Successfully generated {len(generated_files)} programs in {output_dir}")
    print()
    
    if args.no_check:
        print("Skipping type-checking (--no-check flag set)")
        return
    
    # Set up TypeScript compilation environment
    print("Setting up TypeScript compilation environment...")
    
    # Create package.json if it doesn't exist
    package_json = output_dir / "package.json"
    if not package_json.exists():
        package_json.write_text('''{
  "name": "mina-circuits-test",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "o1js": "^1.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
''')
        print("Created package.json")
    
    # Create tsconfig.json if it doesn't exist
    tsconfig_json = output_dir / "tsconfig.json"
    if not tsconfig_json.exists():
        tsconfig_json.write_text('''{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  }
}
''')
        print("Created tsconfig.json")
    
    # Install dependencies if node_modules doesn't exist
    node_modules = output_dir / "node_modules"
    if not node_modules.exists():
        print("Installing npm dependencies (this may take a moment)...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Warning: npm install failed: {result.stderr[:200]}")
        else:
            print("npm dependencies installed successfully")
    
    print()
    
    # Step 1: Type-check each file individually and track results
    print("Step 1: TypeScript type-checking...")
    tsc_passed = []
    tsc_failed = []
    
    for ts_file in generated_files:
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--strict", "--skipLibCheck", 
                 "--moduleResolution", "bundler", "--module", "ESNext", 
                 "--target", "ESNext", ts_file.name],
                cwd=output_dir,
                capture_output=True,
                timeout=60,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  ✓ {ts_file.name}")
                tsc_passed.append(ts_file)
            else:
                print(f"  ✗ {ts_file.name}")
                # Show first error
                errors = (result.stdout + result.stderr).strip().split('\n')
                if errors and errors[0]:
                    print(f"      {errors[0][:100]}")
                tsc_failed.append(ts_file)
        except subprocess.TimeoutExpired:
            print(f"  ⏱ {ts_file.name} (timeout)")
            tsc_failed.append(ts_file)
        except Exception as e:
            print(f"  ✗ {ts_file.name}: {e}")
            tsc_failed.append(ts_file)
    
    print()
    print(f"TypeScript summary: {len(tsc_passed)}/{len(generated_files)} passed")
    print()
    
    if not tsc_passed:
        print("No files passed type-checking, skipping o1js compilation test")
        return
    
    # Step 2: Compile passing files to JS and test with o1js
    print("Step 2: o1js circuit compilation (circuit.compile())...")
    print("Compiling TypeScript to JavaScript...")
    
    # Compile only the files that passed type-checking
    js_files = []
    for ts_file in tsc_passed:
        result = subprocess.run(
            ["npx", "tsc", "--skipLibCheck", 
             "--moduleResolution", "bundler", "--module", "ESNext", 
             "--target", "ESNext", ts_file.name],
            cwd=output_dir,
            capture_output=True,
            timeout=60,
            text=True
        )
        if result.returncode == 0:
            js_files.append(ts_file.stem)
        else:
            print(f"  Warning: Failed to compile {ts_file.name} to JS")
    
    if not js_files:
        print("No files compiled to JavaScript successfully")
        return
    
    print(f"Compiled {len(js_files)} files to JavaScript")
    print()
    
    # Create test runner
    print("Creating test runner...")
    test_script = output_dir / "test-compile.mjs"
    circuit_imports = []
    circuit_tests = []
    
    for i, module_name in enumerate(js_files):
        var_name = f"circuit{i}"
        circuit_imports.append(f"import {{ circuit as {var_name} }} from './{module_name}.js';")
        circuit_tests.append(f'''
  try {{
    console.log('Compiling {module_name}...');
    await {var_name}.compile();
    console.log('✓ {module_name} compiled successfully');
    success++;
  }} catch (e) {{
    console.log('✗ {module_name} failed:', e.message.slice(0, 100));
    failed++;
  }}''')
    
    test_script_content = f'''// Auto-generated test script
{chr(10).join(circuit_imports)}

let success = 0;
let failed = 0;

async function main() {{
  console.log('Testing o1js circuit compilation...');
  console.log();
{"".join(circuit_tests)}
  console.log();
  console.log(`Compilation summary: ${{success}}/${{success + failed}} circuits compiled successfully`);
  process.exit(failed > 0 ? 1 : 0);
}}

main();
'''
    test_script.write_text(test_script_content)
    print(f"Created {test_script.name}")
    
    # Run the test script
    print("Running o1js compilation tests...")
    print()
    
    try:
        result = subprocess.run(
            ["node", "test-compile.mjs"],
            cwd=output_dir,
            capture_output=True,
            timeout=300,  # o1js compile can be slow
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr[:500])
    except subprocess.TimeoutExpired:
        print("⏱ o1js compilation timed out (>5 minutes)")
    except Exception as e:
        print(f"Error running tests: {e}")
    
    # Final summary
    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Generated:        {len(generated_files)} programs")
    print(f"TypeScript pass:  {len(tsc_passed)}/{len(generated_files)}")
    print(f"TypeScript fail:  {len(tsc_failed)}/{len(generated_files)}")
    if tsc_failed:
        print(f"  Failed files: {', '.join(f.stem for f in tsc_failed)}")


if __name__ == "__main__":
    main()
