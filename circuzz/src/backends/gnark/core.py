
from pathlib import Path
from random import Random
import time
from typing import Any

from backends.common.config_shared import GeneratorSource, OracleType
from experiment.data import DataEntry, TestResult

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger
from circuzz.common.smt_fusion import SMTFusionRunConfig, next_smt_fusion_program

from experiment.config import Config, OnlineTuning

from .helper import run_metamorphic_tests, run_smt_pipeline_tests_from_go_source
from .utils import GnarkCurve
from .utils import curve_to_prime
from .picus import ConstraintLevel, generate_picus_constrained_gnark_code, ir_to_gnark_code, run_picus_check

logger = get_color_logger()


def save_error_metamorphic_circuit_pair(save_path: Path, gnark_code: str, gnark_code_tf: str) -> Path:
    error_dir = save_path / "errors"

    num_of_subdirs = len(list(error_dir.glob("error_*")))
    current_error_dir = error_dir / f"error_{num_of_subdirs + 1}"
    current_error_dir.mkdir(parents=True, exist_ok=True)
    with open(current_error_dir / "circuit.go", "w") as f:
        f.write(gnark_code)
    with open(current_error_dir / "circuit_transformed.go", "w") as f:
        f.write(gnark_code_tf)
    return current_error_dir


def run_gnark_metamorphic_tests \
    ( seed: int | float
    , working_dir: Path
    , report_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:

    match config.gnark.oracle_type:
        case OracleType.CIRCUZZ:
            return run_gnark_metamorphic_tests_with_circuzz_oracle(seed, working_dir, report_dir, config, online_tuning)
        case OracleType.PICUS:
            return run_gnark_metamorphic_tests_with_picus_oracle(seed, working_dir, report_dir, config, online_tuning)
        case OracleType.SMT_PIPELINE:
            return run_gnark_smt_pipeline_tests(seed, working_dir, report_dir, config, online_tuning)
        case _:
            raise NotImplementedError(f"unimplemented gnark oracle type '{config.gnark.oracle_type}'")


def run_gnark_smt_pipeline_tests \
    ( seed: int | float
    , working_dir: Path
    , report_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:
    if config.gnark.generator_source != GeneratorSource.SMT_FUSION:
        raise ValueError("smt_pipeline oracle requires 'generator_source' to be 'smt_fusion'")
    if config.gnark.smt_solver_path is None or config.gnark.smt_seed_dir is None:
        raise ValueError("missing SMT fusion config: 'smt_solver_path' and 'smt_seed_dir' are required")
    if config.gnark.smt_num_outputs is None or config.gnark.smt_max_models is None:
        raise ValueError("missing SMT fusion config: 'smt_num_outputs' and 'smt_max_models' are required")

    start_time = time.time()
    fusion_cfg = SMTFusionRunConfig(
        smt_solver_path=config.gnark.smt_solver_path,
        smt_seed_dir=config.gnark.smt_seed_dir,
        dsl="gnark",
        num_outputs=config.gnark.smt_num_outputs,
        max_models=config.gnark.smt_max_models,
        yinyang_config=config.gnark.smt_yinyang_config,
        oracle=config.gnark.smt_oracle,
        max_attempts=config.gnark.smt_max_attempts,
    )
    program = next_smt_fusion_program(report_dir, fusion_cfg, seed)
    data_entries: list[DataEntry] = []

    selected_models = program.models[: min(config.gnark.test_iterations, len(program.models))]
    if len(selected_models) == 0:
        raise RuntimeError(f"program '{program.name}' has no replayable models")
    go_source = program.dsl_path.read_text()
    iterations, go_test_time = run_smt_pipeline_tests_from_go_source(
        circuit_name=program.name,
        go_source=go_source,
        models=selected_models,
        curve=GnarkCurve.BN254,
        working_dir=working_dir / f"smt-{program.name}",
        config=config,
        online_tuning=online_tuning,
    )
    test_time = time.time() - start_time
    has_error = any(iteration.error is not None for iteration in iterations)
    if has_error:
        # SMT mode has only one circuit; store it in the standard error folder.
        error_dir = save_error_metamorphic_circuit_pair(
            report_dir,
            go_source,
            go_source,
        )
        first_error = next((iteration for iteration in iterations if iteration.error is not None), None)
        if first_error is not None:
            diagnostics = [
                f"error={first_error.error}",
                f"go_timeout={first_error.go_timeout}",
                f"go_test_time={go_test_time}",
                "",
                "go_test_output:",
                str(first_error.go_ignored_compiler_error or "<empty>"),
            ]
            (error_dir / "error.txt").write_text("\n".join(diagnostics))

    for idx, iteration in enumerate(iterations):
        data_entries.append(
            DataEntry(
                tool="gnark",
                test_time=test_time,
                seed=seed,
                curve=GnarkCurve.BN254.value,
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
                gnark_go_test_time=go_test_time,
                gnark_go_timeout=iteration.go_timeout,
                gnark_go_ignored_compiler_error=iteration.go_ignored_compiler_error,
            )
        )

    return TestResult(data_entries)

def run_gnark_metamorphic_tests_with_picus_oracle \
    ( seed: int | float
    , working_dir: Path
    , report_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:
        """
        Runs a single metamorphic test using PICUS oracle for constraint checking.
        """
        start_time = time.time()
        logger.info(f"gnark metamorphic testing, seed: {seed}, working-dir: {working_dir}, oracle: PICUS")

        rng = Random(seed)
        ir_gen_seed = rng.randint(1000000000, 9999999999)
        ir_tf_seed = rng.randint(1000000000, 9999999999)
        kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
        curve = rng.choice(list(GnarkCurve))
        prime = curve_to_prime(curve)

        # Timeout settings for PICUS
        PICUS_TIMEOUT_INITIAL = 60   # seconds for initial circuit
        PICUS_TIMEOUT_TRANSFORMED = 360  # seconds for transformed circuit

        ir_generation_start = time.time()
        ir, gnark_code, num_tries = generate_picus_constrained_gnark_code(
            prime, False, config.ir, ir_gen_seed, PICUS_TIMEOUT_INITIAL)

        logger.info(f"Generated PICUS constrained gnark code after {num_tries} tries.")
        logger.info("Original, PICUS Constrained Gnark Code:")
        logger.info(gnark_code)

        ir_generation_time = time.time() - ir_generation_start

        ir_rewrite_start = time.time()
        POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
        gnark_code_tf = ir_to_gnark_code(ir_tf)

        logger.info("Transformed Gnark Code:")
        logger.info(gnark_code_tf)

        ir_rewrite_time = time.time() - ir_rewrite_start

        picus_result = run_picus_check(gnark_code_tf, PICUS_TIMEOUT_TRANSFORMED)

        # Save circuits if error detected:``
        # - UNDER_CONSTRAINED: transformation introduced under-constrained circuit
        # - COMPILATION_FAILURE: transformation produced code that doesn't compile
        #   (original circuit compiled successfully since it passed PICUS check)
        has_error = picus_result.constraint_level in (
            ConstraintLevel.UNDER_CONSTRAINED,
            ConstraintLevel.COMPILATION_FAILURE
        )
        if has_error:
            save_error_metamorphic_circuit_pair(report_dir, gnark_code, gnark_code_tf)

        test_time = time.time() - start_time

        return TestResult([
             DataEntry \
                ( tool = "gnark"
                , test_time = test_time
                , seed = seed
                , curve = curve.value
                , oracle = kind.value
                , iteration = 0
                , error = f"PICUS: {picus_result.constraint_level}" if has_error else None
                , ir_generation_seed = ir_gen_seed
                , ir_generation_time = ir_generation_time
                , ir_rewrite_seed = ir_tf_seed
                , ir_rewrite_time = ir_rewrite_time
                , ir_rewrite_rules = [POI.rule.name for POI in POIs]
                , c1_node_size = ir.node_size()
                , c1_assignments = len(ir.assignments())
                , c1_assertions = len(ir.assertions())
                , c1_assumptions = len(ir.assumptions())
                , c1_input_signals = len(ir.inputs)
                , c1_output_signals = len(ir.outputs)
                , c2_node_size = ir_tf.node_size()
                , c2_assignments = len(ir_tf.assignments())
                , c2_assertions = len(ir_tf.assertions())
                , c2_assumptions = len(ir_tf.assumptions())
                , c2_input_signals = len(ir_tf.inputs)
                , c2_output_signals = len(ir_tf.outputs)
                # PICUS specific data
                , picus_program_generation_reruns = num_tries
                , picus_transformed_constraint_level = picus_result.constraint_level
             )
        ])

def run_gnark_metamorphic_tests_with_circuzz_oracle \
    ( seed: int | float
    , working_dir: Path
    , report_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:

    """
    Runs a single metamorphic test with a given seed using the provided
    working directory and configuration.
    """

    start_time = time.time()
    logger.info(f"gnark metamorphic testing, seed: {seed}, working-dir: {working_dir}, oracle: CIRCUZZ")

    rng = Random(seed)

    test_seed = rng.randint(1000000000, 9999999999)

    circuit_seed_set : set[int] = set()
    while len(circuit_seed_set) < config.gnark.bundle_size:
        circuit_seed_set.add(rng.randint(1000000000, 9999999999))

    circuit_lookup : dict[str, dict[str, Any]] = {} # dummy lookup to track circuits
    pair_and_curves = []
    for circuit_seed in list(circuit_seed_set):

        ir_tf_seed = rng.randint(1000000000, 9999999999)
        kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
        curve = rng.choice(list(GnarkCurve))
        prime = curve_to_prime(curve)

        ir_generation_start = time.time()
        ir = generate_random_circuit(prime, False, config.ir, circuit_seed)
        ir.name = f"C1_{circuit_seed}_{ir_tf_seed}"
        ir_generation_time = time.time() - ir_generation_start

        ir_rewrite_start = time.time()
        POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
        ir_tf.name = f"C2_{circuit_seed}_{ir_tf_seed}"
        ir_rewrite_time = time.time() - ir_rewrite_start

        # add to bundle
        metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)
        pair_and_curves.append((metamorphic_pair, curve))

        # add to entries
        circuit_entry = \
            { "c1_node_size"       : ir.node_size()
            , "c1_assignments"     : len(ir.assignments())
            , "c1_assertions"      : len(ir.assertions())
            , "c1_assumptions"     : len(ir.assumptions())
            , "c1_input_signals"   : len(ir.inputs)
            , "c1_output_signals"  : len(ir.outputs)
            , "c2_node_size"       : ir_tf.node_size()
            , "c2_assignments"     : len(ir_tf.assignments())
            , "c2_assertions"      : len(ir_tf.assertions())
            , "c2_assumptions"     : len(ir_tf.assumptions())
            , "c2_input_signals"   : len(ir_tf.inputs)
            , "c2_output_signals"  : len(ir_tf.outputs)
            , "ir_generation_seed" : circuit_seed
            , "ir_generation_time" : ir_generation_time
            , "ir_rewrite_seed"    : ir_tf_seed
            , "ir_rewrite_time"    : ir_rewrite_time
            , "ir_rewrite_rules"   : [POI.rule.name for POI in POIs]
            , "curve"              : curve.value
            , "oracle"             : kind.value
            }
        circuit_lookup[ir.name] = circuit_entry

    gnark_result = run_metamorphic_tests(pair_and_curves, test_seed, working_dir, config, online_tuning)
    test_time = time.time() - start_time

    # Save circuits if error detected (code already stored in result)
    has_error = any(
        iteration.error is not None
        for iterations_list in gnark_result.iterations.values()
        for iteration in iterations_list
    )
    if has_error:
        # Save the first pair that has an error
        for (metamorphic_pair, _), circuit_info in zip(pair_and_curves, circuit_lookup.values()):
            circuit_name = metamorphic_pair.fst.name
            if circuit_name in gnark_result.iterations and circuit_name in gnark_result.circuit_codes:
                if any(iteration.error is not None for iteration in gnark_result.iterations[circuit_name]):
                    gnark_code_orig, gnark_code_tf = gnark_result.circuit_codes[circuit_name]
                    save_error_metamorphic_circuit_pair(report_dir, gnark_code_orig, gnark_code_tf)
                    break  # Save only the first error pair

    data_entries : list[DataEntry] = []
    for key in circuit_lookup:
        ir_info = circuit_lookup[key]
        for idx, iteration in enumerate(gnark_result.iterations[key]):

            data_entry = DataEntry \
                ( tool = "gnark"
                , test_time = test_time
                , seed = seed
                , curve = ir_info["curve"]
                , oracle = ir_info["oracle"]
                , iteration = idx
                , error = iteration.error
                , ir_generation_seed = ir_info["ir_generation_seed"]
                , ir_generation_time = ir_info["ir_generation_time"]
                , ir_rewrite_seed = ir_info["ir_rewrite_seed"]
                , ir_rewrite_time = ir_info["ir_rewrite_time"]
                , ir_rewrite_rules = ir_info["ir_rewrite_rules"]
                , c1_node_size = ir_info["c1_node_size"]
                , c1_assignments = ir_info["c1_assignments"]
                , c1_assertions = ir_info["c1_assertions"]
                , c1_assumptions = ir_info["c1_assumptions"]
                , c1_input_signals = ir_info["c1_input_signals"]
                , c1_output_signals = ir_info["c1_output_signals"]
                , c2_node_size = ir_info["c2_node_size"]
                , c2_assignments = ir_info["c2_assignments"]
                , c2_assertions = ir_info["c2_assertions"]
                , c2_assumptions = ir_info["c2_assumptions"]
                , c2_input_signals = ir_info["c2_input_signals"]
                , c2_output_signals = ir_info["c2_output_signals"]
                , gnark_c1_compile = iteration.c1_compile
                , gnark_c1_compile_time = iteration.c1_compile_time
                , gnark_c2_compile = iteration.c2_compile
                , gnark_c2_compile_time = iteration.c2_compile_time
                , gnark_c1_new_witness = iteration.c1_new_witness
                , gnark_c1_new_witness_time = iteration.c1_new_witness_time
                , gnark_c2_new_witness = iteration.c2_new_witness
                , gnark_c2_new_witness_time = iteration.c2_new_witness_time
                , gnark_c1_witness_solved = iteration.c1_witness_solved
                , gnark_c1_witness_solved_time = iteration.c1_witness_solved_time
                , gnark_c2_witness_solved = iteration.c2_witness_solved
                , gnark_c2_witness_solved_time = iteration.c2_witness_solved_time
                , gnark_c1_witness_write = iteration.c1_witness_write
                , gnark_c1_witness_write_time = iteration.c1_witness_write_time
                , gnark_c2_witness_write = iteration.c2_witness_write
                , gnark_c2_witness_write_time = iteration.c2_witness_write_time
                , gnark_c1_new_srs = iteration.c1_new_srs
                , gnark_c2_new_srs = iteration.c2_new_srs
                , gnark_c1_proof_setup = iteration.c1_proof_setup
                , gnark_c1_proof_setup_time = iteration.c1_proof_setup_time
                , gnark_c2_proof_setup = iteration.c2_proof_setup
                , gnark_c2_proof_setup_time = iteration.c2_proof_setup_time
                , gnark_c1_prove = iteration.c1_prove
                , gnark_c1_prove_time = iteration.c1_prove_time
                , gnark_c2_prove = iteration.c2_prove
                , gnark_c2_prove_time = iteration.c2_prove_time
                , gnark_c1_witness_public = iteration.c1_witness_public
                , gnark_c1_witness_public_time = iteration.c1_witness_public_time
                , gnark_c2_witness_public = iteration.c2_witness_public
                , gnark_c2_witness_public_time = iteration.c2_witness_public_time
                , gnark_c1_verify = iteration.c1_verify
                , gnark_c1_verify_time = iteration.c1_verify_time
                , gnark_c2_verify = iteration.c2_verify
                , gnark_c2_verify_time = iteration.c2_verify_time
                , gnark_cs_engine = iteration.cs_engine
                , gnark_proof_system = iteration.proof_system
                , gnark_go_test_time = iteration.go_test_time
                , gnark_go_timeout = iteration.go_timeout
                , gnark_go_ignored_compiler_error = iteration.go_ignored_compiler_error
                )

            data_entries.append(data_entry)

    return TestResult(data_entries)
