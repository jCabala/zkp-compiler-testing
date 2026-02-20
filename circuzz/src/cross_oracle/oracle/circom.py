from pathlib import Path
from random import Random
import time
from typing import Callable

from cross_oracle.config.shared import GeneratorSource
from cross_oracle.generation.queue import next_smt_fusion_program
from cross_oracle.generation.types import SMTFusionRunConfig

from backends.circom.helper import run_smt_pipeline_tests_from_source
from backends.circom.utils import CircomCurve, CircomOptimization
from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult


def run_circom_smt_pipeline_tests(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
    save_error_pair: Callable[..., None] | None = None,
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
    if has_error and circom_result.original_code and circom_result.transformed_code and save_error_pair is not None:
        save_error_pair(
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
