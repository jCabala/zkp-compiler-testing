"""
Mina/o1js metamorphic testing helpers.

This module contains utilities for running metamorphic tests on Mina/o1js circuits.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from random import Random
from typing import TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor
import re
import json

from circuzz.common.command import ExecStatus, execute_command
from circuzz.common.field import CurvePrime, random_field_element
from circuzz.common.filesystem import clean_or_create_dir
from circuzz.common.helper import remove_ansi_escape_sequences
from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.colorlogs import get_color_logger
from circuzz.ir.nodes import Circuit

from .ir2mina import IR2MinaVisitor
from .emitter import EmitVisitor
from .config import MinaConfig

if TYPE_CHECKING:
    from experiment.config import OnlineTuning

logger = get_color_logger()

# ================================================================
#                        Constants
# ================================================================

PROJECT_NAME = "circuit"
CIRCUIT_FILENAME = "circuit.ts"
COMPILED_FILENAME = "circuit.js"

# ================================================================
#                        Error Types
# ================================================================


class MinaError(StrEnum):
    """Possible error types detected by Mina tests."""
    DIVERGING_SIGNALS = "diverging signals"
    METAMORPHIC_VIOLATION_EXECUTION = "metamorphic violation execution"
    METAMORPHIC_VIOLATION_VERIFICATION = "metamorphic violation verification"
    PROOF_VERIFICATION_FAILED = "proof verification failed"


# ================================================================
#                        Result Types
# ================================================================


@dataclass
class TestIteration:
    """Represents a single test iteration with timing and error info."""
    # TypeScript compilation (tsc)
    c1_ts_compile: bool | None = None
    c1_ts_compile_time: float | None = None
    c2_ts_compile: bool | None = None
    c2_ts_compile_time: float | None = None
    
    # ZkProgram compilation (circuit.compile())
    c1_zk_compile: bool | None = None
    c1_zk_compile_time: float | None = None
    c2_zk_compile: bool | None = None
    c2_zk_compile_time: float | None = None
    
    # Proving (circuit.compute())
    c1_prove: bool | None = None
    c1_prove_time: float | None = None
    c2_prove: bool | None = None
    c2_prove_time: float | None = None
    
    # Verification
    c1_verify: bool | None = None
    c1_verify_time: float | None = None
    c2_verify: bool | None = None
    c2_verify_time: float | None = None
    
    # Output values
    c1_output: str | None = None
    c2_output: str | None = None
    
    # Ignored errors (known issues)
    c1_ignored_error: str | None = None
    c2_ignored_error: str | None = None
    
    # Stopping error
    error: str | None = None
    
    def is_error(self) -> bool:
        return self.error is not None


@dataclass
class MinaResult:
    """Result of running Mina metamorphic tests."""
    iterations: list[TestIteration] = field(default_factory=list)
    original_code: str | None = None
    transformed_code: str | None = None


# ================================================================
#                     Input Generation
# ================================================================


def random_input(
    input_signals: list[str],
    input_types: list[str],
    curve: CurvePrime,
    boundary_probability: float,
    rng: Random,
) -> dict[str, str]:
    """
    Generate random inputs for a circuit.
    
    Args:
        input_signals: List of input signal names
        input_types: List of input types ("Field" or "Bool")
        curve: Field curve for generating field elements
        boundary_probability: Probability of choosing boundary values
        rng: Random number generator
    
    Returns:
        Dictionary mapping signal names to string values
    """
    input_map: dict[str, str] = {}
    
    for name, typ in zip(input_signals, input_types):
        if typ == "Bool":
            # Boolean: randomly true or false
            input_map[name] = "true" if rng.random() < 0.5 else "false"
        else:
            # Field: use random_field_element with boundary probability
            value = random_field_element(
                curve, rng, 
                exclude_prime=True,
                boundary_prob=boundary_probability
            )
            input_map[name] = str(value)
    
    return input_map


# ================================================================
#                     Code Generation
# ================================================================


def ir_to_mina_code(
    circuit: Circuit, 
    curve: CurvePrime,
    is_boolean_circuit: bool = False,
) -> str:
    """
    Convert IR circuit to Mina/o1js TypeScript code.
    
    Args:
        circuit: Intermediate representation of circuit
        curve: Field curve for the circuit
        is_boolean_circuit: Whether to use Bool type for all signals
    
    Returns:
        TypeScript source code for Mina ZkProgram
    """
    visitor = IR2MinaVisitor(curve, is_boolean_circuit=is_boolean_circuit)
    ast = visitor.transform(circuit)
    emitter = EmitVisitor()
    return emitter.emit(ast)


# ================================================================
#                     Project Setup
# ================================================================


def create_package_json(project_dir: Path) -> Path:
    """Create package.json for o1js project."""
    package_json = {
        "name": "circuit-test",
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "build": "tsc",
            "test": "node --experimental-vm-modules test-runner.mjs"
        },
        "dependencies": {
            "o1js": "^2.2.0"
        },
        "devDependencies": {
            "typescript": "^5.7.0"
        }
    }
    
    path = project_dir / "package.json"
    path.write_text(json.dumps(package_json, indent=2))
    return path


def create_tsconfig(project_dir: Path) -> Path:
    """Create tsconfig.json for TypeScript compilation."""
    tsconfig = {
        "compilerOptions": {
            "target": "ESNext",
            "module": "ESNext",
            "moduleResolution": "bundler",
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
            "resolveJsonModule": True,
            "declaration": False,
            "sourceMap": False,
            "outDir": "."
        },
        "include": ["*.ts"],
        "exclude": ["node_modules"]
    }
    
    path = project_dir / "tsconfig.json"
    path.write_text(json.dumps(tsconfig, indent=2))
    return path


# ================================================================
#                  Stage-Based Test Runners
# ================================================================

COMPILE_AND_PROVE_RUNNER_FILENAME = "compile-and-prove-runner.mjs"
BATCH_RUNNER_FILENAME = "batch-runner.mjs"
BATCH_INPUTS_FILENAME = "batch-inputs.json"
BATCH_RESULTS_FILENAME = "batch-results.json"
VERIFY_RUNNER_FILENAME = "verify-runner.mjs"
VK_FILENAME = "verification-key.json"
PROOF_FILENAME = "proof.json"


def create_compile_and_prove_runner(
    project_dir: Path,
    circuit_name: str,
    inputs: dict[str, str],
    input_types: list[str],
) -> Path:
    """
    Create a merged runner that compiles and proves in a single process.
    This avoids double compilation since o1js caches provers in memory.
    Reports both compile_time_ms and prove_time_ms separately.
    """
    # Build input arguments with correct types
    input_args = []
    for i, (name, value) in enumerate(sorted(inputs.items())):
        typ = input_types[i] if i < len(input_types) else "Field"
        if typ == "Bool":
            input_args.append(f"Bool({value})")
        else:
            input_args.append(f"Field({value}n)")
    
    inputs_str = ", ".join(input_args)
    
    runner_code = f'''// Merged: Compile + Prove circuit (single process to avoid double compilation)
import {{ Field, Bool }} from 'o1js';
import {{ circuit }} from './{circuit_name}.js';
import fs from 'fs';

async function main() {{
    try {{
        // Stage 1: Compile ZkProgram
        const compileStart = Date.now();
        const {{ verificationKey }} = await circuit.compile();
        const compile_time_ms = Date.now() - compileStart;
        
        // Save verification key
        fs.writeFileSync('{VK_FILENAME}', JSON.stringify(verificationKey, null, 2));
        
        // Stage 2: Prove with inputs (prover is now cached in memory)
        const proveStart = Date.now();
        const result = await circuit.compute({inputs_str});
        const prove_time_ms = Date.now() - proveStart;
        
        // Extract public output
        let outputStr;
        if (result.publicOutput === undefined) {{
            outputStr = null;
        }} else if (typeof result.publicOutput.toString === 'function') {{
            outputStr = result.publicOutput.toString();
        }} else {{
            outputStr = JSON.stringify(result.publicOutput);
        }}
        
        // Save proof
        const proofJson = result.proof.toJSON();
        fs.writeFileSync('{PROOF_FILENAME}', JSON.stringify({{
            proof: proofJson,
            publicOutput: outputStr
        }}, null, 2));
        
        console.log(JSON.stringify({{
            success: true,
            stage: "compile_and_prove",
            compile_time_ms,
            prove_time_ms,
            public_output: outputStr
        }}));
    }} catch (error) {{
        // Determine which stage failed based on whether VK exists
        const stage = fs.existsSync('{VK_FILENAME}') ? "prove" : "compile";
        console.log(JSON.stringify({{
            success: false,
            stage,
            error: error.message
        }}));
        process.exit(1);
    }}
}}

main();
'''
    path = project_dir / COMPILE_AND_PROVE_RUNNER_FILENAME
    path.write_text(runner_code)
    return path


def create_batch_runner(
    project_dir: Path,
    circuit_name: str,
    input_types: list[str],
) -> Path:
    """
    Create a batch runner that compiles ONCE, proves and verifies with MULTIPLE input sets.
    This is a major optimization: compile once (~60-130s) then prove many times (~2-5s each).
    Crucially, we now verify EVERY proof immediately after generation.
    
    The runner reads inputs from batch-inputs.json and writes results to batch-results.json.
    Each iteration's results include: success, prove_time_ms, verify_time_ms, public_output, error, verify_error.
    """
    # Build the input parsing logic based on types
    input_parsing = []
    for i, typ in enumerate(input_types):
        if typ == "Bool":
            input_parsing.append(f'inputs[{i}] === "true" ? Bool(true) : Bool(false)')
        else:
            input_parsing.append(f'Field(BigInt(inputs[{i}]))')
    
    input_conversion = ", ".join(input_parsing)
    
    runner_code = f'''// Batch Runner: Compile ONCE, prove MULTIPLE times, verify all
// This avoids recompiling the ZkProgram for each iteration (major speedup!)
import {{ Field, Bool, verify }} from 'o1js';
import {{ circuit }} from './{circuit_name}.js';
import fs from 'fs';

async function main() {{
    const results = {{
        compile_success: false,
        compile_time_ms: 0,
        compile_error: null,
        iterations: []
    }};
    
    try {{
        // Load all input sets
        const batchInputs = JSON.parse(fs.readFileSync('{BATCH_INPUTS_FILENAME}', 'utf-8'));
        
        // Stage 1: Compile ZkProgram ONCE
        console.error('Compiling circuit...');
        const compileStart = Date.now();
        const {{ verificationKey }} = await circuit.compile();
        results.compile_time_ms = Date.now() - compileStart;
        results.compile_success = true;
        console.error(`Compilation completed in ${{results.compile_time_ms}}ms`);
        
        // Save verification key
        fs.writeFileSync('{VK_FILENAME}', JSON.stringify(verificationKey, null, 2));
        
        // Stage 2: Prove and verify with each input set (prover is cached in memory!)
        for (let i = 0; i < batchInputs.length; i++) {{
            const iterResult = {{
                iteration: i,
                success: false,
                prove_time_ms: 0,
                verify_time_ms: 0,
                public_output: null,
                error: null,
                verify_error: null
            }};
            
            try {{
                const inputs = batchInputs[i];
                console.error(`Iteration ${{i + 1}}/${{batchInputs.length}}: Proving...`);
                
                // Convert inputs to o1js types
                const typedInputs = [{input_conversion}];
                
                // Prove
                const proveStart = Date.now();
                const result = await circuit.compute(...typedInputs);
                iterResult.prove_time_ms = Date.now() - proveStart;
                iterResult.success = true;
                
                // Extract public output
                if (result.publicOutput === undefined) {{
                    iterResult.public_output = null;
                }} else if (typeof result.publicOutput.toString === 'function') {{
                    iterResult.public_output = result.publicOutput.toString();
                }} else {{
                    iterResult.public_output = JSON.stringify(result.publicOutput);
                }}
                
                // Verify immediately after proving
                console.error(`  Verifying...`);
                try {{
                    const verifyStart = Date.now();
                    const isValid = await verify(result.proof, verificationKey);
                    iterResult.verify_time_ms = Date.now() - verifyStart;
                    
                    if (!isValid) {{
                        iterResult.verify_error = "Proof verification returned false";
                        console.error(`  Verification failed: proof is invalid`);
                    }} else {{
                        console.error(`  Verified in ${{iterResult.verify_time_ms}}ms`);
                    }}
                }} catch (verifyErr) {{
                    iterResult.verify_error = verifyErr.message;
                    console.error(`  Verification error: ${{verifyErr.message}}`);
                }}
                
                console.error(`  Iteration ${{i + 1}} completed: proved in ${{iterResult.prove_time_ms}}ms, verified in ${{iterResult.verify_time_ms}}ms`);
                
            }} catch (error) {{
                iterResult.error = error.message;
                console.error(`  Iteration ${{i + 1}} prove failed: ${{error.message}}`);
            }}
            
            results.iterations.push(iterResult);
        }}
        
    }} catch (error) {{
        // Compilation failed
        results.compile_error = error.message;
        console.error(`Compilation failed: ${{error.message}}`);
    }}
    
    // Write results to file (for Python to read)
    fs.writeFileSync('{BATCH_RESULTS_FILENAME}', JSON.stringify(results, null, 2));
    
    // Also output summary to stdout
    console.log(JSON.stringify({{
        success: results.compile_success,
        compile_time_ms: results.compile_time_ms,
        iterations_count: results.iterations.length,
        iterations_success: results.iterations.filter(i => i.success).length
    }}));
}}

main();
'''
    path = project_dir / BATCH_RUNNER_FILENAME
    path.write_text(runner_code)
    return path


def create_verify_runner(project_dir: Path, circuit_name: str) -> Path:
    """
    Create a runner that verifies a proof.
    Requires proof.json and verification-key.json from previous stages.
    """
    runner_code = f'''// Stage 3: Verify proof
import {{ verify }} from 'o1js';
import {{ circuit }} from './{circuit_name}.js';
import fs from 'fs';

async function main() {{
    try {{
        // Load verification key
        if (!fs.existsSync('{VK_FILENAME}')) {{
            throw new Error('Verification key not found. Run compile stage first.');
        }}
        const vkData = JSON.parse(fs.readFileSync('{VK_FILENAME}', 'utf-8'));
        
        // Load proof
        if (!fs.existsSync('{PROOF_FILENAME}')) {{
            throw new Error('Proof not found. Run prove stage first.');
        }}
        const proofData = JSON.parse(fs.readFileSync('{PROOF_FILENAME}', 'utf-8'));
        
        const startTime = Date.now();
        const isValid = await verify(proofData.proof, vkData);
        const elapsedTime = Date.now() - startTime;
        
        console.log(JSON.stringify({{
            success: isValid,
            stage: "verify",
            time_ms: elapsedTime,
            verified: isValid
        }}));
        
        if (!isValid) {{
            process.exit(1);
        }}
    }} catch (error) {{
        console.log(JSON.stringify({{
            success: false,
            stage: "verify",
            error: error.message
        }}));
        process.exit(1);
    }}
}}

main();
'''
    path = project_dir / VERIFY_RUNNER_FILENAME
    path.write_text(runner_code)
    return path


def prepare_project(
    root: Path,
    prefix: str,
    circuit: Circuit,
    curve: CurvePrime,
    is_boolean_circuit: bool = False,
) -> tuple[Path, str]:
    """
    Create a complete o1js project for a circuit.
    
    Args:
        root: Root directory for projects
        prefix: Prefix for project directory name
        circuit: Circuit to generate code for
        curve: Field curve
        is_boolean_circuit: Whether this is a boolean circuit
    
    Returns:
        Tuple of (project_path, generated_code)
    """
    # Create project directory
    project_dir = root / f"{prefix}_{circuit.name}"
    clean_or_create_dir(project_dir)
    
    # Generate circuit code
    code = ir_to_mina_code(circuit, curve, is_boolean_circuit)
    
    # Write circuit file
    circuit_path = project_dir / CIRCUIT_FILENAME
    circuit_path.write_text(code)
    
    # Create project files
    create_package_json(project_dir)
    create_tsconfig(project_dir)
    
    # Symlink to preinstalled node_modules (from Docker image)
    # This avoids running npm install for every circuit
    preinstalled_node_modules = Path("/circuzz/programs-mina/node_modules")
    target_node_modules = project_dir / "node_modules"
    if preinstalled_node_modules.exists() and not target_node_modules.exists():
        target_node_modules.symlink_to(preinstalled_node_modules)
    
    return project_dir, code


# ================================================================
#                     Command Execution
# ================================================================


def compile_typescript(
    project_dir: Path,
    timeout: float | None = None,
) -> ExecStatus:
    """
    Compile TypeScript circuit to JavaScript.
    
    Args:
        project_dir: Directory containing the TypeScript files
        timeout: Optional timeout in seconds
    
    Returns:
        ExecStatus with compilation result
    """
    command = ["npx", "tsc", "--noEmit", "false"]
    status = execute_command(
        command,
        identifier="tsc_compile",
        working_dir=project_dir,
        timeout=timeout,
    )
    
    if status.is_failure():
        # TypeScript errors typically go to stdout, not stderr
        error_output = status.stdout or status.stderr
        logger.debug(f"TypeScript compilation failed in {project_dir}:")
        logger.debug(f"  stdout: {status.stdout[:500] if status.stdout else '(empty)'}")
        logger.debug(f"  stderr: {status.stderr[:500] if status.stderr else '(empty)'}")
    else:
        logger.debug(f"TypeScript compilation succeeded in {project_dir}")
    
    return status


# ================================================================
#                     Result Parsing
# ================================================================


def extract_assertion_error(error_msg: str) -> str | None:
    """
    Extract assertion error message from o1js output.
    
    Args:
        error_msg: Raw error message from stderr
    
    Returns:
        Extracted assertion message or None
    """
    # Check for Bool.assertTrue failure
    if "Bool.assertTrue()" in error_msg:
        return "assertion failed: Bool.assertTrue()"
    
    # Check for constraint unsatisfied
    if "Constraint unsatisfied" in error_msg:
        match = re.search(r"Constraint unsatisfied.*?:(.*?)(?:\n|$)", error_msg, re.DOTALL)
        if match:
            return f"constraint unsatisfied: {match.group(1).strip()[:100]}"
        return "constraint unsatisfied"
    
    # Check for general error
    if "Error:" in error_msg:
        match = re.search(r"Error:\s*(.+?)(?:\n|$)", error_msg)
        if match:
            return match.group(1).strip()[:200]
    
    return None


# ================================================================
#                  Stage-Based Execution Functions
# ================================================================


def run_stage_runner(
    project_dir: Path,
    runner_filename: str,
    timeout: float | None = None,
) -> ExecStatus:
    """
    Run a stage-specific runner script.
    
    Args:
        project_dir: Directory containing the runner
        runner_filename: Name of the runner file
        timeout: Optional timeout in seconds
    
    Returns:
        ExecStatus with execution result
    """
    command = ["node", "--experimental-vm-modules", runner_filename]
    return execute_command(
        command,
        identifier=f"node_{runner_filename}",
        working_dir=project_dir,
        timeout=timeout,
    )


def parse_stage_result(status: ExecStatus) -> tuple[bool, dict | None, str | None]:
    """
    Parse the result of a stage execution.
    
    Args:
        status: ExecStatus from running stage runner
    
    Returns:
        Tuple of (success, result_dict, error_message)
    """
    if status.is_timeout:
        return False, None, "timeout"
    
    stdout = status.stdout.strip()
    
    try:
        # Find JSON in output
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                result = json.loads(line)
                if result.get("success"):
                    return True, result, None
                else:
                    return False, result, result.get("error", "unknown error")
    except json.JSONDecodeError:
        pass
    
    # Fallback: check return code
    if status.returncode == 0:
        return True, None, None
    
    # Try to extract error
    stderr = remove_ansi_escape_sequences(status.stderr)
    stdout_clean = remove_ansi_escape_sequences(status.stdout)
    error_msg = extract_assertion_error(stderr) or extract_assertion_error(stdout_clean) or "stage failed"
    return False, None, error_msg


def execute_ts_compile(
    project_dir: Path,
    timeout: float | None = 60.0,
) -> tuple[bool, float | None, str | None]:
    """
    Stage 0: Compile TypeScript to JavaScript.
    
    Args:
        project_dir: Project directory with TypeScript files
        timeout: Compilation timeout
    
    Returns:
        Tuple of (success, compile_time, error_message)
    """
    compiled_file = project_dir / COMPILED_FILENAME
    if compiled_file.exists():
        logger.debug(f"Reusing compiled TypeScript in {project_dir}")
        return True, 0.0, None
    
    logger.debug(f"Compiling TypeScript in {project_dir}...")
    status = compile_typescript(project_dir, timeout=timeout)
    
    if status.is_failure():
        error_output = status.stdout.strip() or status.stderr.strip()
        error_msg = error_output[:500] if error_output else "unknown error"
        return False, status.delta_time, f"ts compilation failed: {error_msg}"
    
    return True, status.delta_time, None


def execute_compile_and_prove(
    project_dir: Path,
    inputs: dict[str, str],
    input_types: list[str],
    timeout: float | None = 300.0,
) -> tuple[bool, float | None, float | None, str | None, str | None, str | None]:
    """
    Merged Stage: Compile ZkProgram and generate proof in a single process.
    This avoids double compilation since o1js caches provers in memory only.
    
    Args:
        project_dir: Project directory with compiled JavaScript
        inputs: Input values
        input_types: Types of inputs
        timeout: Total timeout for compile + prove
    
    Returns:
        Tuple of (success, compile_time, prove_time, public_output, failed_stage, error_message)
        failed_stage is "compile" or "prove" if success is False
    """
    # Create merged runner with inputs
    create_compile_and_prove_runner(project_dir, "circuit", inputs, input_types)
    
    logger.debug(f"Compiling and proving circuit in {project_dir} with inputs: {inputs}")
    status = run_stage_runner(project_dir, COMPILE_AND_PROVE_RUNNER_FILENAME, timeout=timeout)
    success, result, error = parse_stage_result(status)
    
    if success and result:
        compile_time = result.get("compile_time_ms", 0) / 1000.0
        prove_time = result.get("prove_time_ms", 0) / 1000.0
        public_output = result.get("public_output")
        return True, compile_time, prove_time, public_output, None, None
    else:
        # Determine which stage failed
        failed_stage = result.get("stage", "compile") if result else "compile"
        return False, None, None, None, failed_stage, error


def execute_verify(
    project_dir: Path,
    timeout: float | None = 60.0,
) -> tuple[bool, float | None, str | None]:
    """
    Stage 3: Verify the proof.
    
    Args:
        project_dir: Project directory with proof and verification key
        timeout: Verification timeout
    
    Returns:
        Tuple of (success, verify_time, error_message)
    """
    # Create verify runner if not exists
    verify_runner = project_dir / VERIFY_RUNNER_FILENAME
    if not verify_runner.exists():
        create_verify_runner(project_dir, "circuit")
    
    logger.debug(f"Verifying proof in {project_dir}...")
    status = run_stage_runner(project_dir, VERIFY_RUNNER_FILENAME, timeout=timeout)
    success, result, error = parse_stage_result(status)
    
    verify_time = result.get("time_ms", 0) / 1000.0 if result else status.delta_time
    
    return success, verify_time, error


@dataclass
class BatchIterationResult:
    """Result of a single iteration within a batch run."""
    iteration: int
    success: bool
    prove_time: float | None
    verify_time: float | None
    public_output: str | None
    error: str | None
    verify_error: str | None = None


@dataclass
class BatchResult:
    """Result of running a batch of iterations for a single circuit."""
    compile_success: bool
    compile_time: float | None
    compile_error: str | None
    iterations: list[BatchIterationResult]


def execute_batch_compile_and_prove(
    project_dir: Path,
    all_inputs: list[dict[str, str]],
    input_types: list[str],
    timeout: float | None = 600.0,
) -> BatchResult:
    """
    Batch execution: Compile ONCE and prove with MULTIPLE input sets.
    This is a major optimization over running compile+prove for each iteration.
    
    Args:
        project_dir: Project directory with compiled JavaScript
        all_inputs: List of input dictionaries (one per iteration)
        input_types: Types of inputs
        timeout: Total timeout for compile + all proves
    
    Returns:
        BatchResult with compile results and list of iteration results
    """
    # Create batch runner
    create_batch_runner(project_dir, "circuit", input_types)
    
    # Write inputs to JSON file (sorted keys for consistency)
    inputs_for_json = []
    for inputs in all_inputs:
        # Convert dict to list (sorted by key) for JavaScript to consume
        sorted_values = [inputs[k] for k in sorted(inputs.keys())]
        inputs_for_json.append(sorted_values)
    
    inputs_file = project_dir / BATCH_INPUTS_FILENAME
    inputs_file.write_text(json.dumps(inputs_for_json))
    
    logger.debug(f"Running batch compile+prove+verify in {project_dir} with {len(all_inputs)} iterations")
    status = run_stage_runner(project_dir, BATCH_RUNNER_FILENAME, timeout=timeout)
    
    # Read results from file (more reliable than parsing stdout)
    results_file = project_dir / BATCH_RESULTS_FILENAME
    if results_file.exists():
        try:
            raw_results = json.loads(results_file.read_text())
            
            iterations = []
            for iter_data in raw_results.get("iterations", []):
                iterations.append(BatchIterationResult(
                    iteration=iter_data.get("iteration", 0),
                    success=iter_data.get("success", False),
                    prove_time=iter_data.get("prove_time_ms", 0) / 1000.0 if iter_data.get("prove_time_ms") else None,
                    verify_time=iter_data.get("verify_time_ms", 0) / 1000.0 if iter_data.get("verify_time_ms") else None,
                    public_output=iter_data.get("public_output"),
                    error=iter_data.get("error"),
                    verify_error=iter_data.get("verify_error"),
                ))
            
            return BatchResult(
                compile_success=raw_results.get("compile_success", False),
                compile_time=raw_results.get("compile_time_ms", 0) / 1000.0 if raw_results.get("compile_time_ms") else None,
                compile_error=raw_results.get("compile_error"),
                iterations=iterations,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse batch results: {e}")
    
    # Fallback if results file doesn't exist or is malformed
    error_msg = "batch execution failed"
    if status.is_timeout:
        error_msg = "timeout"
    elif status.stderr:
        error_msg = remove_ansi_escape_sequences(status.stderr)[:200]
    
    return BatchResult(
        compile_success=False,
        compile_time=None,
        compile_error=error_msg,
        iterations=[],
    )


# ================================================================
#                     Metamorphic Testing
# ================================================================


def is_assertion_error(error: str | None) -> bool:
    """Check if an error is an assertion failure (expected for random circuits)."""
    if error is None:
        return False
    assertion_patterns = [
        "assertion failed",
        "Bool.assertTrue",
        "constraint unsatisfied",
    ]
    error_lower = error.lower()
    return any(pattern.lower() in error_lower for pattern in assertion_patterns)


def run_metamorphic_tests(
    metamorphic_pair: MetamorphicCircuitPair,
    test_seed: int,
    curve: CurvePrime,
    working_dir: Path,
    config: MinaConfig,
    is_boolean_circuit: bool = False,
    online_tuning: 'OnlineTuning | None' = None,
) -> MinaResult:
    """
    Run metamorphic tests on a circuit pair using batch mode only.
    
    Args:
        metamorphic_pair: Original and transformed circuit pair
        test_seed: Seed for test input generation
        curve: Field curve for the circuits
        working_dir: Directory for test execution
        config: Mina test configuration
        is_boolean_circuit: Whether this is a boolean circuit
        online_tuning: Optional online tuning for prove/verify stages
    
    Returns:
        MinaResult with all test iterations
    """
    return run_metamorphic_tests_batch(
        metamorphic_pair=metamorphic_pair,
        test_seed=test_seed,
        curve=curve,
        working_dir=working_dir,
        config=config,
        is_boolean_circuit=is_boolean_circuit,
        online_tuning=online_tuning,
    )

def run_metamorphic_tests_batch(
    metamorphic_pair: MetamorphicCircuitPair,
    test_seed: int,
    curve: CurvePrime,
    working_dir: Path,
    config: MinaConfig,
    is_boolean_circuit: bool = False,
    online_tuning: 'OnlineTuning | None' = None,
) -> MinaResult:
    """
    Run metamorphic tests with batch optimization: compile once, prove many times.
    
    This is a significant optimization over run_metamorphic_tests() which recompiles
    on every iteration. Here we:
    1. TypeScript compile both circuits (once)
    2. Generate ALL inputs upfront
    3. Batch compile+prove: ZK compile once, prove N times with different inputs
    4. Process all results
    
    Args:
        metamorphic_pair: Original and transformed circuit pair
        test_seed: Seed for test input generation
        curve: Field curve for the circuits
        working_dir: Directory for test execution
        config: Mina test configuration
        is_boolean_circuit: Whether this is a boolean circuit
        online_tuning: Optional online tuning for prove/verify stages
    
    Returns:
        MinaResult with all test iterations
    """
    result = MinaResult()
    rng = Random(test_seed)
    
    c1_circuit = metamorphic_pair.fst
    c2_circuit = metamorphic_pair.snd
    
    # Prepare projects
    c1_project, c1_code = prepare_project(
        working_dir, "c1", c1_circuit, curve, is_boolean_circuit
    )
    c2_project, c2_code = prepare_project(
        working_dir, "c2", c2_circuit, curve, is_boolean_circuit
    )
    
    result.original_code = c1_code
    result.transformed_code = c2_code
    
    # Log generated code
    logger.info("Original Mina/o1js Code:")
    logger.info(c1_code)
    logger.info("Transformed Mina/o1js Code:")
    logger.info(c2_code)
    
    # ================================================================
    # Stage 0: TypeScript Compilation (ONCE for each circuit)
    # ================================================================
    
    ts_compile_timeout = 60.0
    
    logger.debug("Stage 0: TypeScript compilation (batch mode)...")
    
    c1_ts_success, c1_ts_time, c1_ts_error = execute_ts_compile(c1_project, ts_compile_timeout)
    if not c1_ts_success:
        # Create single failed iteration
        iteration = TestIteration()
        iteration.c1_ts_compile = False
        iteration.c1_ts_compile_time = c1_ts_time
        iteration.error = f"c1 ts compilation failed: {c1_ts_error}"
        result.iterations.append(iteration)
        return result
    
    c2_ts_success, c2_ts_time, c2_ts_error = execute_ts_compile(c2_project, ts_compile_timeout)
    if not c2_ts_success:
        iteration = TestIteration()
        iteration.c1_ts_compile = True
        iteration.c1_ts_compile_time = c1_ts_time
        iteration.c2_ts_compile = False
        iteration.c2_ts_compile_time = c2_ts_time
        iteration.error = f"c2 ts compilation failed: {c2_ts_error}"
        result.iterations.append(iteration)
        return result
    
    logger.debug(f"TypeScript compilation done: c1={c1_ts_time:.2f}s, c2={c2_ts_time:.2f}s")
    
    # ================================================================
    # Generate ALL inputs upfront
    # ================================================================
    
    input_types = ["Bool" if is_boolean_circuit else "Field"] * len(c1_circuit.inputs)
    
    all_inputs: list[dict[str, str]] = []
    for i in range(config.test_iterations):
        inputs = random_input(
            c1_circuit.inputs,
            input_types,
            curve,
            config.boundary_input_probability,
            rng,
        )
        all_inputs.append(inputs)
    
    logger.debug(f"Generated {len(all_inputs)} input sets for batch execution")
    
    # ================================================================
    # Stage 1: Batch Compile + Prove (PARALLEL execution for C1 and C2)
    # ================================================================
    
    # Calculate generous timeout: base compile (180s) + 30s per prove iteration
    batch_timeout = 180.0 + (30.0 * config.test_iterations)
    
    logger.info(f"Stage 1: Batch compile+prove+verify (c1 & c2 in parallel: {config.test_iterations} iterations each)...")
    
    # Run C1 and C2 in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        future_c1 = executor.submit(
            execute_batch_compile_and_prove,
            c1_project, all_inputs, input_types, batch_timeout
        )
        future_c2 = executor.submit(
            execute_batch_compile_and_prove,
            c2_project, all_inputs, input_types, batch_timeout
        )
        
        # Wait for both to complete
        c1_batch_result = future_c1.result()
        c2_batch_result = future_c2.result()
    
    logger.debug(f"Batch execution done: c1_compile={c1_batch_result.compile_success} ({c1_batch_result.compile_time or 0:.2f}s), "
                f"c2_compile={c2_batch_result.compile_success} ({c2_batch_result.compile_time or 0:.2f}s)")
    
    # ================================================================
    # Process Results into TestIterations
    # ================================================================
    
    # Handle compile failures in a metamorphic way
    # We cannot proceed if either circuit failed to compile
    if not c1_batch_result.compile_success or not c2_batch_result.compile_success:
        iteration = TestIteration()
        iteration.c1_ts_compile = True
        iteration.c1_ts_compile_time = c1_ts_time
        iteration.c2_ts_compile = True
        iteration.c2_ts_compile_time = c2_ts_time
        iteration.c1_zk_compile = c1_batch_result.compile_success
        iteration.c1_zk_compile_time = c1_batch_result.compile_time
        iteration.c2_zk_compile = c2_batch_result.compile_success
        iteration.c2_zk_compile_time = c2_batch_result.compile_time
        # If both failed, treat as ignorable (no error, just record ignored errors)
        if not c1_batch_result.compile_success and not c2_batch_result.compile_success:
            iteration.c1_ignored_error = f"c1 ZK compile failed: {c1_batch_result.compile_error}"
            iteration.c2_ignored_error = f"c2 ZK compile failed: {c2_batch_result.compile_error}"
            logger.debug("Both c1 and c2 ZK compile failed (ignored)")
        else:
            # Only one failed: this is a metamorphic violation
            if not c1_batch_result.compile_success:
                iteration.error = f"c1 ZK compile failed: {c1_batch_result.compile_error}"
                logger.warning("Metamorphic violation: c1 ZK compile failed but c2 succeeded")
            else:
                iteration.error = f"c2 ZK compile failed: {c2_batch_result.compile_error}"
                logger.warning("Metamorphic violation: c2 ZK compile failed but c1 succeeded")
        result.iterations.append(iteration)
        return result
    
    # Process iteration results
    for i in range(config.test_iterations):
        iteration = TestIteration()
        
        # TS compilation times (shared across iterations, but attribute to first)
        if i == 0:
            iteration.c1_ts_compile = True
            iteration.c1_ts_compile_time = c1_ts_time
            iteration.c2_ts_compile = True
            iteration.c2_ts_compile_time = c2_ts_time
            iteration.c1_zk_compile = True
            iteration.c1_zk_compile_time = c1_batch_result.compile_time
            iteration.c2_zk_compile = True
            iteration.c2_zk_compile_time = c2_batch_result.compile_time
        else:
            iteration.c1_ts_compile = True
            iteration.c2_ts_compile = True
            iteration.c1_zk_compile = True
            iteration.c2_zk_compile = True
        
        # Get iteration results
        c1_iter = c1_batch_result.iterations[i] if i < len(c1_batch_result.iterations) else None
        c2_iter = c2_batch_result.iterations[i] if i < len(c2_batch_result.iterations) else None
        
        if c1_iter is None or c2_iter is None:
            iteration.error = f"Missing batch results for iteration {i}"
            result.iterations.append(iteration)
            break
        
        # Prove results
        iteration.c1_prove = c1_iter.success
        iteration.c1_prove_time = c1_iter.prove_time
        iteration.c1_output = c1_iter.public_output
        iteration.c1_verify = c1_iter.verify_error is None  # True if no verify error
        iteration.c1_verify_time = c1_iter.verify_time
        
        iteration.c2_prove = c2_iter.success
        iteration.c2_prove_time = c2_iter.prove_time
        iteration.c2_output = c2_iter.public_output
        iteration.c2_verify = c2_iter.verify_error is None  # True if no verify error
        iteration.c2_verify_time = c2_iter.verify_time
        
        # Metamorphic comparison
        c1_success = c1_iter.success
        c2_success = c2_iter.success
        c1_error = c1_iter.error
        c2_error = c2_iter.error
        c1_verify_error = c1_iter.verify_error
        c2_verify_error = c2_iter.verify_error
        
        c1_assertion_fail = not c1_success and is_assertion_error(c1_error)
        c2_assertion_fail = not c2_success and is_assertion_error(c2_error)
        
        # Case 1: Both failed with assertions - this is OK
        if c1_assertion_fail and c2_assertion_fail:
            iteration.c1_ignored_error = c1_error
            iteration.c2_ignored_error = c2_error
            logger.debug(f"Iteration {i+1}: Both circuits failed with assertions (ignored)")
            result.iterations.append(iteration)
            continue
        
        # Case 2: c1 failed but c2 succeeded - metamorphic violation!
        if not c1_success and c2_success:
            iteration.error = MinaError.METAMORPHIC_VIOLATION_EXECUTION
            logger.warning(f"Iteration {i+1}: Metamorphic violation - c1 failed but c2 succeeded")
            result.iterations.append(iteration)
            break
        
        # Case 3: c1 succeeded but c2 failed - metamorphic violation!
        if c1_success and not c2_success:
            iteration.error = MinaError.METAMORPHIC_VIOLATION_EXECUTION
            logger.warning(f"Iteration {i+1}: Metamorphic violation - c1 succeeded but c2 failed")
            result.iterations.append(iteration)
            break
        
        # Case 4: Both failed with non-assertion errors
        if not c1_success and not c2_success:
            iteration.c1_ignored_error = c1_error
            iteration.c2_ignored_error = c2_error
            logger.debug(f"Iteration {i+1}: Both circuits failed (ignored)")
            result.iterations.append(iteration)
            continue
        
        # Case 5: Both proved successfully - check verification and outputs
        # NEW: Check verification status
        c1_verify_ok = c1_verify_error is None
        c2_verify_ok = c2_verify_error is None
        
        # Case 5a: One verified but the other didn't - metamorphic violation!
        if c1_verify_ok and not c2_verify_ok:
            iteration.error = MinaError.METAMORPHIC_VIOLATION_VERIFICATION
            logger.warning(f"Iteration {i+1}: Metamorphic violation - c1 verified but c2 failed: {c2_verify_error}")
            result.iterations.append(iteration)
            break
        
        if not c1_verify_ok and c2_verify_ok:
            iteration.error = MinaError.METAMORPHIC_VIOLATION_VERIFICATION
            logger.warning(f"Iteration {i+1}: Metamorphic violation - c2 verified but c1 failed: {c1_verify_error}")
            result.iterations.append(iteration)
            break
        
        # Case 5b: Both failed verification - record and continue
        if not c1_verify_ok and not c2_verify_ok:
            iteration.c1_ignored_error = c1_verify_error
            iteration.c2_ignored_error = c2_verify_error
            logger.debug(f"Iteration {i+1}: Both circuits failed verification (ignored): c1={c1_verify_error}, c2={c2_verify_error}")
            result.iterations.append(iteration)
            continue
        
        # Case 5c: Both verified successfully - check outputs match
        if c1_iter.public_output != c2_iter.public_output:
            iteration.error = MinaError.DIVERGING_SIGNALS
            logger.warning(f"Iteration {i+1}: Diverging outputs - c1={c1_iter.public_output}, c2={c2_iter.public_output}")
            result.iterations.append(iteration)
            break
        
        logger.debug(f"Iteration {i+1}: passed (output={c1_iter.public_output}, verified)")
        result.iterations.append(iteration)
        
        # Update online tuning
        if online_tuning is not None:
            if c1_iter.prove_time:
                online_tuning.add_prove_or_verify_time(c1_iter.prove_time)
            if c1_iter.verify_time:
                online_tuning.add_prove_or_verify_time(c1_iter.verify_time)
            if c2_iter.prove_time:
                online_tuning.add_prove_or_verify_time(c2_iter.prove_time)
            if c2_iter.verify_time:
                online_tuning.add_prove_or_verify_time(c2_iter.verify_time)
    
    # Add compile times to online tuning (once, at the end)
    if online_tuning is not None:
        online_tuning.add_general_execution_time(c1_ts_time)
        online_tuning.add_general_execution_time(c2_ts_time)
        if c1_batch_result.compile_time:
            online_tuning.add_general_execution_time(c1_batch_result.compile_time)
        if c2_batch_result.compile_time:
            online_tuning.add_general_execution_time(c2_batch_result.compile_time)
    
    return result
