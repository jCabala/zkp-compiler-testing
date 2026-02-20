from pathlib import Path
from random import Random
import time
import shutil

from backends.common.config_shared import GeneratorSource, OracleType
from backends.circom.emitter import EmitConfig
from backends.circom.picus import (
    ConstraintLevel,
    generate_picus_constrained_circom_code,
    ir_to_circom_code,
    run_picus_check,
)
from experiment.data import DataEntry, TestResult

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger
from circuzz.common.smt_fusion import SMTFusionRunConfig, next_smt_fusion_program

from experiment.config import Config, OnlineTuning

from .helper import run_metamorphic_tests, run_smt_pipeline_tests_from_source
from .utils import curve_to_prime
from .utils import CircomCurve, CircomOptimization

logger = get_color_logger()


# ============================================================
# Error artifact saving (enhanced)
# ============================================================

def _safe_copy(src: Path, dst: Path) -> None:
    """
    Best-effort copy, never raises (fuzzer must not crash when archiving).
    """
    try:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    except Exception:
        pass


def _safe_copytree(src_dir: Path, dst_dir: Path) -> None:
    """
    Best-effort directory copy (Python 3.8+ has dirs_exist_ok).
    """
    try:
        if src_dir.exists() and src_dir.is_dir():
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    except Exception:
        pass


def save_error_metamorphic_circuit_pair(
    save_path: Path,
    circom_code: str,
    circom_code_tf: str,
    *,
    working_dir: Path | None = None,
):
    """
    Saves:
      - circuit.circom + circuit_transformed.circom (always)
      - plus, if working_dir is given: copies the full `origin/` and `transformed/`
        project folders so you keep:
          - input.json
          - generate_witness.js
          - circuit.wasm
          - witness.*.wtns
          - proof/public (if produced)
          - commands.md (your dump_commands output)
          - plus any snarkjs/circom intermediate files produced
    """
    error_dir = save_path / "errors"
    error_dir.mkdir(parents=True, exist_ok=True)

    num_of_subdirs = len(list(error_dir.glob("error_*")))
    current_error_dir = error_dir / f"error_{num_of_subdirs + 1}"
    current_error_dir.mkdir(parents=True, exist_ok=True)

    (current_error_dir / "circuit.circom").write_text(circom_code)
    (current_error_dir / "circuit_transformed.circom").write_text(circom_code_tf)

    # NEW: archive the working project folders (contains exact stderr/stdout in commands.md,
    # witness-gen js/wasm, witnesses, etc.)
    if working_dir is not None:
        _safe_copytree(working_dir / "origin", current_error_dir / "origin")
        _safe_copytree(working_dir / "transformed", current_error_dir / "transformed")


# ============================================================
# Entry points
# ============================================================

def run_circom_metamorphic_tests(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:

    match config.circom.oracle_type:
        case OracleType.CIRCUZZ:
            return run_circom_metamorphic_tests_with_circuzz_oracle(
                seed, working_dir, report_dir, config, online_tuning
            )
        case OracleType.PICUS:
            return run_circom_metamorphic_tests_with_picus_oracle(
                seed, working_dir, report_dir, config, online_tuning
            )
        case OracleType.SMT_PIPELINE:
            return run_circom_smt_pipeline_tests(
                seed, working_dir, report_dir, config, online_tuning
            )
        case _:
            raise NotImplementedError(
                f"unimplemented circom oracle type '{config.circom.oracle_type}'"
            )


def run_circom_smt_pipeline_tests(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:
    if config.circom.generator_source != GeneratorSource.SMT_FUSION:
        raise ValueError("smt_pipeline oracle requires 'generator_source' to be 'smt_fusion'")
    if config.circom.smt_solver_path is None or config.circom.smt_seed_dir is None:
        raise ValueError("missing SMT fusion config: 'smt_solver_path' and 'smt_seed_dir' are required")
    if config.circom.smt_num_outputs is None or config.circom.smt_max_models is None:
        raise ValueError("missing SMT fusion config: 'smt_num_outputs' and 'smt_max_models' are required")

    start_time = time.time()
    rng = Random(seed)
    if rng.random() < config.circom.smt_bn128_probability:
        curve = CircomCurve.BN128
    else:
        non_bn128_curves = [c for c in CircomCurve if c != CircomCurve.BN128]
        curve = rng.choice(non_bn128_curves)
    fusion_cfg = SMTFusionRunConfig(
        smt_solver_path=config.circom.smt_solver_path,
        smt_seed_dir=config.circom.smt_seed_dir,
        dsl="circom",
        num_outputs=config.circom.smt_num_outputs,
        max_models=config.circom.smt_max_models,
        yinyang_config=config.circom.smt_yinyang_config,
        oracle=config.circom.smt_oracle,
        max_attempts=config.circom.smt_max_attempts,
    )
    program = next_smt_fusion_program(report_dir, fusion_cfg, seed)
    data_entries: list[DataEntry] = []
    optimization = rng.choice(list(CircomOptimization))

    selected_models = program.models[: min(config.circom.test_iterations, len(program.models))]
    if len(selected_models) == 0:
        raise RuntimeError(f"program '{program.name}' has no replayable models")
    model_working_dir = working_dir / f"smt-{program.name}"
    circom_source = program.dsl_path.read_text()
    circom_result = run_smt_pipeline_tests_from_source(
        circuit_name=f"SMT_{program.name}",
        circom_source=circom_source,
        models=selected_models,
        curve=curve,
        optimization=optimization,
        rng=rng,
        working_dir=model_working_dir,
        config=config,
        online_tuning=online_tuning,
    )
    test_time = time.time() - start_time
    has_error = any(iteration.error is not None for iteration in circom_result.iterations)
    if has_error and circom_result.original_code and circom_result.transformed_code:
        save_error_metamorphic_circuit_pair(
            report_dir,
            circom_result.original_code,
            circom_result.transformed_code,
            working_dir=model_working_dir,
        )

    for idx, iteration in enumerate(circom_result.iterations):
        data_entries.append(
            DataEntry(
                tool="circom",
                test_time=test_time,
                seed=seed,
                curve=curve.value,
                oracle="smt_pipeline",
                iteration=idx,
                error=iteration.error,
                ir_generation_seed=0,
                ir_generation_time=0,
                ir_rewrite_seed=0,
                ir_rewrite_time=0,
                ir_rewrite_rules=[],
                c1_node_size=0,
                c1_assignments=0,
                c1_assertions=0,
                c1_assumptions=0,
                c1_input_signals=0,
                c1_output_signals=0,
                c2_node_size=0,
                c2_assignments=0,
                c2_assertions=0,
                c2_assumptions=0,
                c2_input_signals=0,
                c2_output_signals=0,
                circom_c1_compilation=iteration.compilation.get(f"SMT_{program.name}", None),
                circom_c1_compilation_time=iteration.compilation_time.get(f"SMT_{program.name}", None),
                circom_c1_compilation_optimization=iteration.compilation_optimization.get(f"SMT_{program.name}", None),
                circom_c1_cpp_witness_preparation=iteration.cpp_witness_preparation.get(f"SMT_{program.name}", None),
                circom_c1_cpp_witness_preparation_time=iteration.cpp_witness_preparation_time.get(f"SMT_{program.name}", None),
                circom_c1_cpp_witness_generation=iteration.cpp_witness_generation.get(f"SMT_{program.name}", None),
                circom_c1_cpp_witness_generation_time=iteration.cpp_witness_generation_time.get(f"SMT_{program.name}", None),
                circom_c1_js_witness_generation=iteration.js_witness_generation.get(f"SMT_{program.name}", None),
                circom_c1_js_witness_generation_time=iteration.js_witness_generation_time.get(f"SMT_{program.name}", None),
                circom_c1_snarkjs_witness_check=iteration.snarkjs_witness_check.get(f"SMT_{program.name}", None),
                circom_c1_snarkjs_witness_check_time=iteration.snarkjs_witness_check_time.get(f"SMT_{program.name}", None),
                circom_proof_system=iteration.proof_system,
                circom_c1_zkey_generation=iteration.zkey_generation.get(f"SMT_{program.name}", None),
                circom_c1_zkey_generation_time=iteration.zkey_generation_time.get(f"SMT_{program.name}", None),
                circom_c1_proof_generation=iteration.proof_generation.get(f"SMT_{program.name}", None),
                circom_c1_proof_generation_time=iteration.proof_generation_time.get(f"SMT_{program.name}", None),
                circom_c1_vkey_generation=iteration.vkey_generation.get(f"SMT_{program.name}", None),
                circom_c1_vkey_generation_time=iteration.vkey_generation_time.get(f"SMT_{program.name}", None),
                circom_c1_verification=iteration.verification.get(f"SMT_{program.name}", None),
                circom_c1_verification_time=iteration.verification_time.get(f"SMT_{program.name}", None),
                circom_c1_ignored_error=iteration.ignored_error.get(f"SMT_{program.name}", None),
            )
        )

    return TestResult(data_entries)


def run_circom_metamorphic_tests_with_picus_oracle(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:
    start_time = time.time()
    logger.info(
        f"circom metamorphic testing, seed: {seed}, working-dir: {working_dir}, oracle: PICUS"
    )

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
    curve = random_circom_curve(rng)
    prime = curve_to_prime(curve)
    emit_config = EmitConfig(
        constrain_equality_assertions=config.circom.constrain_equality_assertions,
        constrain_sharp_inequality_assertions=config.circom.constrain_sharp_inequality_assertions,
    )

    ir_generation_start = time.time()
    ir, circom_code, num_tries = generate_picus_constrained_circom_code(
        prime, False, config.ir, ir_gen_seed, emit_config=emit_config
    )

    logger.info(f"Generated PICUS constrained circom code after {num_tries} tries.")
    logger.info("Original, PICUS Constrained Circom Code:")
    logger.info(circom_code)

    ir_generation_time = time.time() - ir_generation_start

    ir_rewrite_start = time.time()
    POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
    circom_code_tf = ir_to_circom_code(ir_tf, emit_config=emit_config)

    logger.info("Transformed Circom Code:")
    logger.info(circom_code_tf)

    ir_rewrite_time = time.time() - ir_rewrite_start

    picus_result = run_picus_check(circom_code_tf)

    # Save circuits if error detected
    has_error = picus_result.constraint_level == ConstraintLevel.UNDER_CONSTRAINED
    if has_error:
        # NOTE: PICUS mode doesn't use working_dir origin/transformed projects,
        # so we only save the sources here.
        save_error_metamorphic_circuit_pair(report_dir, circom_code, circom_code_tf)

    test_time = time.time() - start_time

    return TestResult(
        [
            DataEntry(
                tool="circom",
                test_time=test_time,
                seed=seed,
                curve=curve.value,
                oracle=kind.value,
                iteration=0,
                error=f"PICUS: {picus_result.constraint_level}" if has_error else None,
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
                # Picus-specific
                picus_program_generation_reruns=num_tries,
                picus_transformed_constraint_level=picus_result.constraint_level,
            )
        ]
    )


def run_circom_metamorphic_tests_with_circuzz_oracle(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:
    """
    Runs a single metamorphic test with a given seed using the provided
    working directory and configuration.
    """

    start_time = time.time()
    logger.info(
        f"circom metamorphic testing, seed: {seed}, working-dir: {working_dir}, oracle: CIRCUZZ"
    )

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
    curve = random_circom_curve(rng)
    prime = curve_to_prime(curve)

    ir_generation_start = time.time()
    ir = generate_random_circuit(prime, False, config.ir, ir_gen_seed)
    ir.name = f"Circuit_{curve}"
    ir_generation_time = time.time() - ir_generation_start

    ir_rewrite_start = time.time()
    POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
    postfix = "_eq" if kind == MetamorphicKind.EQUAL else "_wk"
    ir_tf.name = f"{ir.name}{postfix}"
    ir_rewrite_time = time.time() - ir_rewrite_start

    metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)

    # IMPORTANT: run_metamorphic_tests creates working_dir/origin and working_dir/transformed.
    # On early-stop error, those folders contain commands.md + witness-gen artifacts.
    circom_result = run_metamorphic_tests(
        metamorphic_pair, test_seed, curve, working_dir, config, online_tuning
    )

    test_time = time.time() - start_time

    # Save circuits + error bundle (projects) if error detected
    has_error = any(iteration.error is not None for iteration in circom_result.iterations)
    if has_error and circom_result.original_code and circom_result.transformed_code:
        save_error_metamorphic_circuit_pair(
            report_dir,
            circom_result.original_code,
            circom_result.transformed_code,
            working_dir=working_dir,  # NEW: copies origin/ + transformed/ folders
        )

    # report each iteration outcome
    data_entries: list[DataEntry] = []
    c1_name = ir.name
    c2_name = ir_tf.name

    for idx, iteration in enumerate(circom_result.iterations):
        data_entry = DataEntry(
            tool="circom",
            test_time=test_time,
            seed=seed,
            curve=curve.value,
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
            circom_c1_compilation=iteration.compilation.get(c1_name, None),
            circom_c1_compilation_time=iteration.compilation_time.get(c1_name, None),
            circom_c1_compilation_optimization=iteration.compilation_optimization.get(
                c1_name, None
            ),
            circom_c2_compilation=iteration.compilation.get(c2_name, None),
            circom_c2_compilation_time=iteration.compilation_time.get(c2_name, None),
            circom_c2_compilation_optimization=iteration.compilation_optimization.get(
                c2_name, None
            ),
            circom_c1_cpp_witness_preparation=iteration.cpp_witness_preparation.get(
                c1_name, None
            ),
            circom_c1_cpp_witness_preparation_time=iteration.cpp_witness_preparation_time.get(
                c1_name, None
            ),
            circom_c1_cpp_witness_generation=iteration.cpp_witness_generation.get(
                c1_name, None
            ),
            circom_c1_cpp_witness_generation_time=iteration.cpp_witness_generation_time.get(
                c1_name, None
            ),
            circom_c1_js_witness_generation=iteration.js_witness_generation.get(
                c1_name, None
            ),
            circom_c1_js_witness_generation_time=iteration.js_witness_generation_time.get(
                c1_name, None
            ),
            circom_c1_snarkjs_witness_check=iteration.snarkjs_witness_check.get(
                c1_name, None
            ),
            circom_c1_snarkjs_witness_check_time=iteration.snarkjs_witness_check_time.get(
                c1_name, None
            ),
            circom_c2_cpp_witness_preparation=iteration.cpp_witness_preparation.get(
                c2_name, None
            ),
            circom_c2_cpp_witness_preparation_time=iteration.cpp_witness_preparation_time.get(
                c2_name, None
            ),
            circom_c2_cpp_witness_generation=iteration.cpp_witness_generation.get(
                c2_name, None
            ),
            circom_c2_cpp_witness_generation_time=iteration.cpp_witness_generation_time.get(
                c2_name, None
            ),
            circom_c2_js_witness_generation=iteration.js_witness_generation.get(
                c2_name, None
            ),
            circom_c2_js_witness_generation_time=iteration.js_witness_generation_time.get(
                c2_name, None
            ),
            circom_c2_snarkjs_witness_check=iteration.snarkjs_witness_check.get(
                c2_name, None
            ),
            circom_c2_snarkjs_witness_check_time=iteration.snarkjs_witness_check_time.get(
                c2_name, None
            ),
            circom_proof_system=iteration.proof_system,
            circom_c1_zkey_generation=iteration.zkey_generation.get(c1_name, None),
            circom_c1_zkey_generation_time=iteration.zkey_generation_time.get(c1_name, None),
            circom_c1_proof_generation=iteration.proof_generation.get(c1_name, None),
            circom_c1_proof_generation_time=iteration.proof_generation_time.get(
                c1_name, None
            ),
            circom_c2_zkey_generation=iteration.zkey_generation.get(c2_name, None),
            circom_c2_zkey_generation_time=iteration.zkey_generation_time.get(c2_name, None),
            circom_c2_proof_generation=iteration.proof_generation.get(c2_name, None),
            circom_c2_proof_generation_time=iteration.proof_generation_time.get(
                c2_name, None
            ),
            circom_c1_vkey_generation=iteration.vkey_generation.get(c1_name, None),
            circom_c1_vkey_generation_time=iteration.vkey_generation_time.get(
                c1_name, None
            ),
            circom_c1_verification=iteration.verification.get(c1_name, None),
            circom_c1_verification_time=iteration.verification_time.get(c1_name, None),
            circom_c2_vkey_generation=iteration.vkey_generation.get(c2_name, None),
            circom_c2_vkey_generation_time=iteration.vkey_generation_time.get(
                c2_name, None
            ),
            circom_c2_verification=iteration.verification.get(c2_name, None),
            circom_c2_verification_time=iteration.verification_time.get(c2_name, None),
            circom_c1_ignored_error=iteration.ignored_error.get(c1_name, None),
            circom_c2_ignored_error=iteration.ignored_error.get(c2_name, None),
        )

        data_entries.append(data_entry)

    return TestResult(data_entries)
