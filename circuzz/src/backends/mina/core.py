"""
Mina/o1js backend core testing logic.

This module implements the main metamorphic testing pipeline for Mina/o1js circuits.
"""

from pathlib import Path
from random import Random
import shutil
import time

from circuzz.common.metamorphism import MetamorphicCircuitPair, MetamorphicKind
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.field import CurvePrime, get_curve_name
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger
from circuzz.ir.config import GeneratorKind

from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult

from .helper import run_metamorphic_tests

logger = get_color_logger()


def _safe_copytree(src_dir: Path, dst_dir: Path) -> None:
    """
    Best-effort directory copy for saving artifacts.
    """
    try:
        if src_dir.exists() and src_dir.is_dir():
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    except Exception:
        pass


def save_error_metamorphic_circuit_pair(
    save_path: Path,
    mina_code: str,
    mina_code_tf: str,
    *,
    working_dir: Path | None = None,
):
    """
    Save error circuit pair to disk for inspection.
    Saves:
      - circuit.ts + circuit_transformed.ts (always)
      - plus, if working_dir is given: copies full c1_* and c2_* project folders
        to keep:
          - generated TypeScript and JavaScript
          - verification-key.json
          - batch-inputs.json, batch-results.json
          - proof.json (if generated)
          - package.json, tsconfig.json
          - any execution logs and artifacts
    
    Args:
        save_path: Base directory for saving errors
        mina_code: Original Mina/o1js code
        mina_code_tf: Transformed Mina/o1js code
        working_dir: Optional working directory containing project folders
    """
    error_dir = save_path / "errors"
    error_dir.mkdir(parents=True, exist_ok=True)
    
    num_of_subdirs = len(list(error_dir.glob("error_*")))
    current_error_dir = error_dir / f"error_{num_of_subdirs + 1}"
    current_error_dir.mkdir(parents=True, exist_ok=True)
    
    (current_error_dir / "circuit.ts").write_text(mina_code)
    (current_error_dir / "circuit_transformed.ts").write_text(mina_code_tf)
    
    # Copy complete project directories with all artifacts
    if working_dir is not None:
        # Find c1 and c2 project directories
        for project_dir in working_dir.iterdir():
            if project_dir.is_dir() and (project_dir.name.startswith("c1_") or project_dir.name.startswith("c2_")):
                _safe_copytree(project_dir, current_error_dir / project_dir.name)


def run_mina_metamorphic_tests(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:
    """
    Run a single metamorphic test with a given seed.
    
    Args:
        seed: Random seed for test generation
        working_dir: Working directory for test execution
        report_dir: Directory for saving error reports
        config: Test configuration
        online_tuning: Online tuning parameters
    
    Returns:
        TestResult with all test iterations and metadata
    """
    start_time = time.time()
    logger.info(f"mina metamorphic testing, seed: {seed}, working-dir: {working_dir}")
    
    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
    
    # Mina/o1js uses Pallas curve (part of Pasta curves)
    curve_prime = CurvePrime.PALLAS
    curve_name = get_curve_name(curve_prime)
    
    # Generate original circuit
    logger.debug(f"Generating circuit with seed {ir_gen_seed}, generator: {config.ir.generation.generator}")
    ir_generation_start = time.time()
    ir = generate_random_circuit(curve_prime, True, config.ir, ir_gen_seed)
    ir.name = f"Circuit_{curve_name}"
    ir_generation_time = time.time() - ir_generation_start
    logger.debug(f"Generated circuit: inputs={ir.inputs}, outputs={ir.outputs}, statements={len(ir.statements)}")
    
    # Apply metamorphic transformation
    logger.debug(f"Applying metamorphic transformation (kind={kind}) with seed {ir_tf_seed}")
    ir_rewrite_start = time.time()
    POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, curve_prime, config.ir, ir_tf_seed)
    postfix = "_eq" if kind == MetamorphicKind.EQUAL else "_wk"
    ir_tf.name = f"{ir.name}{postfix}"
    ir_rewrite_time = time.time() - ir_rewrite_start
    logger.debug(f"Transformed circuit: inputs={ir_tf.inputs}, outputs={ir_tf.outputs}, rules applied: {[p.rule.name for p in POIs]}")
    
    # Determine if this is a boolean circuit
    is_boolean_circuit = config.ir.generation.generator == GeneratorKind.BOOLEAN
    logger.debug(f"Generator kind: {config.ir.generation.generator}, is_boolean_circuit: {is_boolean_circuit}")
    
    # Create metamorphic pair and run tests
    metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)
    mina_result = run_metamorphic_tests(
        metamorphic_pair,
        test_seed,
        curve_prime,
        working_dir,
        config.mina,
        is_boolean_circuit=is_boolean_circuit,
        online_tuning=online_tuning,
    )
    test_time = time.time() - start_time
    logger.debug(f"Metamorphic testing complete: {len(mina_result.iterations)} iterations")
    
    # Save circuits if error detected
    has_error = any(iteration.error is not None for iteration in mina_result.iterations)
    logger.debug(f"Has error: {has_error}")
    if has_error and mina_result.original_code and mina_result.transformed_code:
        save_error_metamorphic_circuit_pair(
            report_dir, 
            mina_result.original_code, 
            mina_result.transformed_code,
            working_dir=working_dir,
        )
    
    # Create data entries for each iteration
    data_entries: list[DataEntry] = []
    for idx, iteration in enumerate(mina_result.iterations):
        data_entry = DataEntry(
            tool="mina",
            test_time=test_time,
            seed=seed,
            curve=curve_name,
            oracle=kind.value,
            iteration=idx,
            error=iteration.error,
            ir_generation_seed=ir_gen_seed,
            ir_generation_time=ir_generation_time,
            ir_rewrite_seed=ir_tf_seed,
            ir_rewrite_time=ir_rewrite_time,
            ir_rewrite_rules=[POI.rule.name for POI in POIs],
            c1_node_size=ir.node_size(),
            c1_assignments=len(ir.assignments()),
            c1_assertions=len(ir.assertions()),
            c1_assumptions=len(ir.assumptions()),
            c1_input_signals=len(ir.inputs),
            c1_output_signals=len(ir.outputs),
            c2_node_size=ir_tf.node_size(),
            c2_assignments=len(ir_tf.assignments()),
            c2_assertions=len(ir_tf.assertions()),
            c2_assumptions=len(ir_tf.assumptions()),
            c2_input_signals=len(ir_tf.inputs),
            c2_output_signals=len(ir_tf.outputs),
            # Mina-specific fields (separated pipeline stages)
            mina_c1_ts_compile=iteration.c1_ts_compile,
            mina_c1_ts_compile_time=iteration.c1_ts_compile_time,
            mina_c2_ts_compile=iteration.c2_ts_compile,
            mina_c2_ts_compile_time=iteration.c2_ts_compile_time,
            mina_c1_zk_compile=iteration.c1_zk_compile,
            mina_c1_zk_compile_time=iteration.c1_zk_compile_time,
            mina_c2_zk_compile=iteration.c2_zk_compile,
            mina_c2_zk_compile_time=iteration.c2_zk_compile_time,
            mina_c1_prove=iteration.c1_prove,
            mina_c1_prove_time=iteration.c1_prove_time,
            mina_c2_prove=iteration.c2_prove,
            mina_c2_prove_time=iteration.c2_prove_time,
            mina_c1_verify=iteration.c1_verify,
            mina_c1_verify_time=iteration.c1_verify_time,
            mina_c2_verify=iteration.c2_verify,
            mina_c2_verify_time=iteration.c2_verify_time,
            mina_c1_ignored_error=iteration.c1_ignored_error,
            mina_c2_ignored_error=iteration.c2_ignored_error,
        )
        data_entries.append(data_entry)
    
    logger.debug(f"Returning TestResult with {len(data_entries)} entries")
    return TestResult(entries=data_entries)
