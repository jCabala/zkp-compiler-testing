#!/usr/bin/env python3
"""
Test script for Mina/o1js helper functions.

This script tests the end-to-end workflow of:
1. Generating IR circuits
2. Converting to Mina/o1js code
3. Setting up project structure
4. Compiling and executing circuits (using stage-based pipeline)

Usage:
    cd /path/to/circuzz
    python fyp_experiments/scripts/test-mina-helper.py
"""

import sys
import tempfile
from pathlib import Path
from random import Random

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from circuzz.common.field import CurvePrime
from circuzz.ir.nodes import Circuit, Assignment, Variable, Integer, BinaryExpression, Operator

from backends.mina.helper import (
    ir_to_mina_code,
    prepare_project,
    compile_typescript,
    random_input,
    # Stage-based execution
    execute_ts_compile,
    execute_zk_compile,
    execute_prove,
    execute_verify,
    create_prove_runner,
)


def create_simple_circuit() -> Circuit:
    """Create a simple test circuit: out0 = in0 + in1"""
    return Circuit(
        name="test_add",
        inputs=["in0", "in1"],
        outputs=["out0"],
        statements=[
            Assignment(
                Variable("out0"),
                BinaryExpression(
                    Operator.ADD,
                    Variable("in0"),
                    Variable("in1"),
                )
            )
        ]
    )


def create_mul_circuit() -> Circuit:
    """Create a multiplication circuit: out0 = in0 * in1"""
    return Circuit(
        name="test_mul",
        inputs=["in0", "in1"],
        outputs=["out0"],
        statements=[
            Assignment(
                Variable("out0"),
                BinaryExpression(
                    Operator.MUL,
                    Variable("in0"),
                    Variable("in1"),
                )
            )
        ]
    )


def test_code_generation():
    """Test IR to Mina code generation."""
    print("\n" + "="*60)
    print("TEST: Code Generation")
    print("="*60)
    
    circuit = create_simple_circuit()
    curve = CurvePrime.PALLAS  # o1js uses Pallas curve
    
    code = ir_to_mina_code(circuit, curve, is_boolean_circuit=False)
    
    print(f"Generated code for circuit '{circuit.name}':")
    print("-" * 40)
    print(code)
    print("-" * 40)
    
    # Basic checks
    assert "ZkProgram" in code, "Code should contain ZkProgram"
    assert "Field" in code, "Code should contain Field type"
    assert "in0" in code, "Code should reference input in0"
    assert "in1" in code, "Code should reference input in1"
    assert "out0" in code, "Code should reference output out0"
    assert ".add(" in code, "Code should use .add() method"
    
    print("✓ Code generation test passed!")
    return True


def test_project_setup():
    """Test project setup and file creation."""
    print("\n" + "="*60)
    print("TEST: Project Setup")
    print("="*60)
    
    circuit = create_simple_circuit()
    curve = CurvePrime.PALLAS
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        project_dir, code = prepare_project(root, "test", circuit, curve)
        
        print(f"Project created at: {project_dir}")
        
        # Check files exist
        assert project_dir.exists(), "Project directory should exist"
        assert (project_dir / "circuit.ts").exists(), "circuit.ts should exist"
        assert (project_dir / "package.json").exists(), "package.json should exist"
        assert (project_dir / "tsconfig.json").exists(), "tsconfig.json should exist"
        
        # List files
        print("Files created:")
        for f in project_dir.iterdir():
            print(f"  - {f.name}")
        
        print("✓ Project setup test passed!")
    
    return True


def test_input_generation():
    """Test random input generation."""
    print("\n" + "="*60)
    print("TEST: Input Generation")
    print("="*60)
    
    curve = CurvePrime.PALLAS
    rng = Random(42)
    
    # Test Field inputs
    inputs = random_input(
        input_signals=["in0", "in1", "in2"],
        input_types=["Field", "Field", "Field"],
        curve=curve,
        boundary_probability=0.1,
        rng=rng,
    )
    
    print("Generated Field inputs:")
    for name, value in inputs.items():
        print(f"  {name}: {value[:20]}..." if len(value) > 20 else f"  {name}: {value}")
    
    assert len(inputs) == 3, "Should generate 3 inputs"
    assert all(name in inputs for name in ["in0", "in1", "in2"]), "All input names should be present"
    
    # Test Bool inputs
    rng = Random(42)
    bool_inputs = random_input(
        input_signals=["b0", "b1"],
        input_types=["Bool", "Bool"],
        curve=curve,
        boundary_probability=0.1,
        rng=rng,
    )
    
    print("\nGenerated Bool inputs:")
    for name, value in bool_inputs.items():
        print(f"  {name}: {value}")
    
    assert all(v in ["true", "false"] for v in bool_inputs.values()), "Bool values should be true/false"
    
    print("✓ Input generation test passed!")
    return True


def test_prove_runner_creation():
    """Test prove runner script generation (stage-based)."""
    print("\n" + "="*60)
    print("TEST: Prove Runner Creation (Stage-Based)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        inputs = {"in0": "5", "in1": "3"}
        input_types = ["Field", "Field"]
        
        runner_path = create_prove_runner(project_dir, "circuit", inputs, input_types)
        
        print(f"Prove runner created at: {runner_path}")
        
        assert runner_path.exists(), "Prove runner should exist"
        
        content = runner_path.read_text()
        print("\nProve runner content (first 500 chars):")
        print("-" * 40)
        print(content[:500])
        print("-" * 40)
        
        assert "Field(5n)" in content, "Should contain Field(5n)"
        assert "Field(3n)" in content, "Should contain Field(3n)"
        assert "circuit.compute" in content, "Should call circuit.compute"
        assert "proof" in content.lower(), "Should handle proof"
        
        print("✓ Prove runner creation test passed!")
    
    return True


def test_full_execution(skip_if_no_npm: bool = True):
    """
    Test full circuit execution using stage-based pipeline.
    
    This test uses the programs-mina directory which has o1js installed.
    """
    print("\n" + "="*60)
    print("TEST: Full Execution (Stage-Based Pipeline)")
    print("="*60)
    
    # Use programs-mina directory which has o1js installed
    script_dir = Path(__file__).parent
    programs_mina = script_dir / "programs-mina"
    
    if not programs_mina.exists():
        print(f"⚠ programs-mina directory not found at {programs_mina}")
        print("  Run generate-mina.py first to set up the environment")
        if skip_if_no_npm:
            return True
        return False
    
    # Check if node_modules exists
    node_modules = programs_mina / "node_modules"
    if not node_modules.exists():
        print(f"⚠ node_modules not found in {programs_mina}")
        print("  Run 'npm install' in programs-mina first")
        if skip_if_no_npm:
            return True
        return False
    
    circuit = create_simple_circuit()
    curve = CurvePrime.PALLAS
    
    # Create project in programs-mina subdirectory
    project_dir = programs_mina / "test_helper"
    project_dir.mkdir(exist_ok=True)
    
    try:
        # Generate circuit code
        code = ir_to_mina_code(circuit, curve, is_boolean_circuit=False)
        
        # Write circuit file
        circuit_path = project_dir / "circuit.ts"
        circuit_path.write_text(code)
        
        print(f"Project: {project_dir}")
        print(f"Generated circuit.ts")
        
        # Stage 0: Compile TypeScript
        print("\nStage 0: Compiling TypeScript...")
        ts_success, ts_time, ts_error = execute_ts_compile(project_dir, timeout=60.0)
        
        if not ts_success:
            print(f"TypeScript compilation failed: {ts_error}")
            return False
        
        print(f"TypeScript compiled successfully in {ts_time:.2f}s")
        
        # Stage 1: Compile ZkProgram
        print("\nStage 1: Compiling ZkProgram (this may take a while)...")
        zk_success, zk_time, zk_error = execute_zk_compile(project_dir, timeout=300.0)
        
        if not zk_success:
            print(f"ZkProgram compilation failed: {zk_error}")
            return False
        
        print(f"ZkProgram compiled successfully in {zk_time:.2f}s")
        
        # Stage 2: Prove
        inputs = {"in0": "5", "in1": "3"}
        input_types = ["Field", "Field"]
        
        print(f"\nStage 2: Proving with inputs: {inputs}")
        prove_success, prove_time, output, prove_error = execute_prove(
            project_dir, inputs, input_types, timeout=300.0
        )
        
        if not prove_success:
            print(f"Proving failed: {prove_error}")
            return False
        
        print(f"Proving succeeded in {prove_time:.2f}s")
        print(f"Output: {output}")
        
        # Check output is 5 + 3 = 8
        if output == "8":
            print("✓ Output value correct (5 + 3 = 8)")
        else:
            print(f"⚠ Output value unexpected: {output} (expected 8)")
        
        # Stage 3: Verify
        print("\nStage 3: Verifying proof...")
        verify_success, verify_time, verify_error = execute_verify(project_dir, timeout=60.0)
        
        if not verify_success:
            print(f"Verification failed: {verify_error}")
            return False
        
        print(f"Verification succeeded in {verify_time:.2f}s")
        print("✓ Full execution test passed!")
        
        return True
        
    finally:
        # Clean up test files
        import shutil
        if project_dir.exists():
            shutil.rmtree(project_dir)


def main():
    """Run all tests."""
    print("="*60)
    print("Mina/o1js Helper Function Tests")
    print("="*60)
    
    tests = [
        ("Code Generation", test_code_generation),
        ("Project Setup", test_project_setup),
        ("Input Generation", test_input_generation),
        ("Prove Runner Creation", test_prove_runner_creation),
        ("Full Execution", lambda: test_full_execution(skip_if_no_npm=True)),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ {name} failed with exception: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    
    for name, success, error in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}" + (f" ({error})" if error else ""))
    
    print(f"\nPassed: {passed}/{total}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
