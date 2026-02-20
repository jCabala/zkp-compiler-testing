from pathlib import Path
import time
from typing import Callable

from cross_oracle.config.shared import GeneratorSource
from cross_oracle.generation.queue import next_smt_fusion_program
from cross_oracle.generation.types import SMTFusionRunConfig

from backends.gnark.helper import run_smt_pipeline_tests_from_go_source
from backends.gnark.utils import GnarkCurve
from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult


def run_gnark_smt_pipeline_tests(
    seed: int | float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
    save_error_pair: Callable[[Path, str, str], Path] | None = None,
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
    if has_error and save_error_pair is not None:
        # SMT mode has only one circuit; store it in the standard error folder.
        error_dir = save_error_pair(
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
