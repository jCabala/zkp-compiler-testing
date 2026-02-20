from pathlib import Path
from random import Random
import re
import time
import shutil

from backends.common.config_shared import GeneratorSource, OracleType
from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.field  import CurvePrime, get_curve_name
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger
from circuzz.common.smt_fusion import SMTFusionRunConfig, next_smt_fusion_program
from circuzz.common.filesystem import clean_or_create_dir

from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult

from .helper import run_metamorphic_tests, run_smt_pipeline_tests_from_project

logger = get_color_logger()


def save_error_metamorphic_circuit_pair(save_path: Path, noir_code: str, noir_code_tf: str) -> Path:
    error_dir = save_path / "errors"

    num_of_subdirs = len(list(error_dir.glob("error_*")))
    current_error_dir = error_dir / f"error_{num_of_subdirs + 1}"
    current_error_dir.mkdir(parents=True, exist_ok=True)
    with open(current_error_dir / "circuit.nr", "w") as f:
        f.write(noir_code)
    with open(current_error_dir / "circuit_transformed.nr", "w") as f:
        f.write(noir_code_tf)
    return current_error_dir


def run_noir_metamorphic_tests \
    ( seed: float
    , working_dir: Path
    , report_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:

    if config.noir.oracle_type == OracleType.SMT_PIPELINE:
        return run_noir_smt_pipeline_tests(seed, working_dir, report_dir, config, online_tuning)

    """
    Runs a single metamorphic test with a given seed using the provided
    working directory and configuration.
    """

    start_time = time.time()
    logger.info(f"noir metamorphic testing, seed: {seed}, working-dir: {working_dir}")

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)

    curve_prime = CurvePrime.BN254 # noir only supports the bn254 curve natively 
    curve_name = get_curve_name(curve_prime)

    ir_generation_start = time.time()
    ir = generate_random_circuit(curve_prime, True, config.ir, ir_gen_seed)
    ir.name = f"Circuit_{curve_name}"
    ir_generation_time = time.time() - ir_generation_start

    ir_rewrite_start = time.time()
    POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, curve_prime, config.ir, ir_tf_seed)
    postfix = "_eq" if kind == MetamorphicKind.EQUAL else "_wk"
    ir_tf.name = f"{ir.name}{postfix}"
    ir_rewrite_time = time.time() - ir_rewrite_start

    metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)
    noir_result = run_metamorphic_tests(metamorphic_pair, test_seed, curve_prime, working_dir, config, online_tuning)
    test_time = time.time() - start_time

    # Save circuits if error detected (code already stored in result)
    has_error = any(iteration.error is not None for iteration in noir_result.iterations)
    if has_error and noir_result.original_code and noir_result.transformed_code:
        save_error_metamorphic_circuit_pair(report_dir, noir_result.original_code, noir_result.transformed_code)

    data_entries : list[DataEntry] = []
    for idx, iteration in enumerate(noir_result.iterations):

        data_entry = DataEntry \
            ( tool = "noir"
            , test_time = test_time
            , seed = seed
            , curve = curve_name
            , oracle = kind.value
            , iteration = idx
            , error = iteration.error
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
            , noir_inliner_aggressiveness = iteration.noir_inliner_aggressiveness
            , noir_c1_execute = iteration.c1_execute
            , noir_c1_execute_time = iteration.c1_execute_time
            , noir_c2_execute = iteration.c2_execute
            , noir_c2_execute_time = iteration.c2_execute_time
            , noir_c1_vk =  iteration.c1_vk
            , noir_c1_vk_time = iteration.c1_vk_time
            , noir_c2_vk =  iteration.c2_vk
            , noir_c2_vk_time = iteration.c2_vk_time
            , noir_c1_bb_prove = iteration.c1_bb_prove
            , noir_c1_bb_prove_time = iteration.c1_bb_prove_time
            , noir_c2_bb_prove = iteration.c2_bb_prove
            , noir_c2_bb_prove_time = iteration.c2_bb_prove_time
            , noir_c1_bb_verify = iteration.c1_bb_verify
            , noir_c1_bb_verify_time = iteration.c1_bb_verify_time
            , noir_c2_bb_verify = iteration.c2_bb_verify
            , noir_c2_bb_verify_time = iteration.c2_bb_verify_time
            , noir_c1_ignored_error = iteration.c1_ignored_error
            , noir_c2_ignored_error = iteration.c2_ignored_error
            )

        data_entries.append(data_entry)

    return TestResult(data_entries)


def _extract_noir_inputs(main_noir_source: str) -> list[str]:
    # Keep this non-greedy so return tuple types like `-> pub (bool, bool)`
    # do not get captured as input parameters.
    signature_match = re.search(r"pub fn main\s*\((.*?)\)\s*(?:->|{)", main_noir_source, re.DOTALL)
    if signature_match is None:
        return []
    args = signature_match.group(1).strip()
    if args == "":
        return []
    result: list[str] = []
    for part in args.split(","):
        token = part.strip()
        if token == "":
            continue
        name = token.split(":")[0].strip()
        if name:
            result.append(name)
    return result


def run_noir_smt_pipeline_tests(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:
    if config.noir.generator_source != GeneratorSource.SMT_FUSION:
        raise ValueError("smt_pipeline oracle requires 'generator_source' to be 'smt_fusion'")
    if config.noir.smt_solver_path is None or config.noir.smt_seed_dir is None:
        raise ValueError("missing SMT fusion config: 'smt_solver_path' and 'smt_seed_dir' are required")
    if config.noir.smt_num_outputs is None or config.noir.smt_max_models is None:
        raise ValueError("missing SMT fusion config: 'smt_num_outputs' and 'smt_max_models' are required")

    start_time = time.time()
    rng = Random(seed)
    fusion_cfg = SMTFusionRunConfig(
        smt_solver_path=config.noir.smt_solver_path,
        smt_seed_dir=config.noir.smt_seed_dir,
        dsl="noir",
        num_outputs=config.noir.smt_num_outputs,
        max_models=config.noir.smt_max_models,
        yinyang_config=config.noir.smt_yinyang_config,
        oracle=config.noir.smt_oracle,
        max_attempts=config.noir.smt_max_attempts,
    )
    program = next_smt_fusion_program(report_dir, fusion_cfg, seed)
    data_entries: list[DataEntry] = []

    selected_models = program.models[: min(config.noir.test_iterations, len(program.models))]
    if len(selected_models) == 0:
        raise RuntimeError(f"program '{program.name}' has no replayable models")

    # SMT-fusion queue may provide either:
    # 1) Noir project directory (.../fused_xxxx)
    # 2) Noir entry source file (.../fused_xxxx/src/main.nr)
    if program.dsl_path.is_dir():
        source_project_dir = program.dsl_path
    elif program.dsl_path.is_file() and program.dsl_path.name == "main.nr":
        source_project_dir = program.dsl_path.parent.parent
    else:
        raise RuntimeError(
            f"expected Noir project directory or src/main.nr path at '{program.dsl_path}'"
        )
    if not source_project_dir.is_dir():
        raise RuntimeError(f"unable to resolve Noir project directory at '{source_project_dir}'")

    model_working_dir = working_dir / f"smt-{program.name}"
    clean_or_create_dir(model_working_dir)
    shutil.copytree(source_project_dir, model_working_dir / "origin", dirs_exist_ok=True)
    project_dir = model_working_dir / "origin"
    source_path = project_dir / "src" / "main.nr"
    if not source_path.is_file():
        raise RuntimeError(f"missing Noir entry source at '{source_path}'")
    required_inputs = _extract_noir_inputs(source_path.read_text())
    noir_result = run_smt_pipeline_tests_from_project(
        project_dir=project_dir,
        models=selected_models,
        required_inputs=required_inputs,
        online_tuning=online_tuning,
        rng=rng,
        witness_only=config.noir.smt_witness_only,
    )
    test_time = time.time() - start_time
    has_error = any(iteration.error is not None for iteration in noir_result.iterations)
    if has_error and noir_result.original_code:
        error_dir = save_error_metamorphic_circuit_pair(
            report_dir,
            noir_result.original_code,
            noir_result.original_code,
        )
        first_error = next((iteration for iteration in noir_result.iterations if iteration.error is not None), None)
        if first_error is not None:
            diagnostics = [
                f"error={first_error.error}",
                f"execute_time={first_error.c1_execute_time}",
                "",
                "noir_output:",
                str(first_error.c1_ignored_error or "<empty>"),
            ]
            (error_dir / "error.txt").write_text("\n".join(diagnostics))

    for idx, iteration in enumerate(noir_result.iterations):
        data_entries.append(
            DataEntry(
                tool="noir",
                test_time=test_time,
                seed=seed,
                curve=get_curve_name(CurvePrime.BN254),
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
                noir_inliner_aggressiveness=iteration.noir_inliner_aggressiveness,
                noir_c1_execute=iteration.c1_execute,
                noir_c1_execute_time=iteration.c1_execute_time,
                noir_c1_vk=iteration.c1_vk,
                noir_c1_vk_time=iteration.c1_vk_time,
                noir_c1_bb_prove=iteration.c1_bb_prove,
                noir_c1_bb_prove_time=iteration.c1_bb_prove_time,
                noir_c1_bb_verify=iteration.c1_bb_verify,
                noir_c1_bb_verify_time=iteration.c1_bb_verify_time,
                noir_c1_ignored_error=iteration.c1_ignored_error,
            )
        )

    return TestResult(data_entries)
