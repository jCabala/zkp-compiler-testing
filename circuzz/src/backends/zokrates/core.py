# -----------------------------
# backends/zokrates/core.py
# -----------------------------
from __future__ import annotations

from pathlib import Path
from random import Random
import time
import shutil

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger
from circuzz.common.field import CurvePrime, get_curve_name

from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult

from .helper import run_metamorphic_tests

logger = get_color_logger()


# ============================================================
# Error artifact saving (same idea as circom)
# ============================================================


def _safe_copytree(src_dir: Path, dst_dir: Path) -> None:
    try:
        if src_dir.exists() and src_dir.is_dir():
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    except Exception:
        pass


def save_error_metamorphic_circuit_pair(
    save_path: Path,
    zok_code: str,
    zok_code_tf: str,
    *,
    working_dir: Path | None = None,
) -> None:
    """
    Saves:
      - circuit.zok + circuit_transformed.zok (always)
      - plus, if working_dir is given: copies full origin/ and transformed/ folders
        to keep:
          - generated .zok
          - out/* logs (compile.log, witness.log, etc.)
          - witness files
          - any future setup/proof/verify artifacts you add
    """
    error_dir = save_path / "errors"
    error_dir.mkdir(parents=True, exist_ok=True)

    num_of_subdirs = len(list(error_dir.glob("error_*")))
    current_error_dir = error_dir / f"error_{num_of_subdirs + 1}"
    current_error_dir.mkdir(parents=True, exist_ok=True)

    (current_error_dir / "circuit.zok").write_text(zok_code)
    (current_error_dir / "circuit_transformed.zok").write_text(zok_code_tf)

    if working_dir is not None:
        _safe_copytree(working_dir / "origin", current_error_dir / "origin")
        _safe_copytree(working_dir / "transformed", current_error_dir / "transformed")


# ============================================================
# Entry point
# ============================================================

def run_zokrates_metamorphic_tests(
    seed: float,
    working_dir: Path,
    report_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> TestResult:
    """
    Mirrors circom/noir:
      - generate IR
      - rewrite IR (metamorphic)
      - run backend pipeline for origin+transformed in working_dir/{origin,transformed}
      - if error, archive everything
      - return per-iteration DataEntry
    """
    start_time = time.time()
    logger.info(f"zokrates metamorphic testing, seed: {seed}, working-dir: {working_dir}")

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)

    # ZoKrates default target is BN254 (aka alt_bn128 / bn128 in many toolchains)
    curve_prime = CurvePrime.BN254
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

    # IMPORTANT: run_metamorphic_tests is expected to create:
    #   working_dir/origin
    #   working_dir/transformed
    # and put all backend artifacts there (sources, logs, witnesses, etc.)
    zokrates_result = run_metamorphic_tests(
        metamorphic_pair, test_seed, curve_prime, working_dir, config, online_tuning
    )

    test_time = time.time() - start_time

    # Detect if any iteration has a known error
    is_known_error = any(
        iteration.error in [
            "unreachable code",
            "assertion obviously false",
            "dynamic comparison incomplete",
            "not implemented",
            "division by zero",
            "unconstrained variables",
        ] or
        iteration.c1_ignored_error in [
            "unreachable code",
            "assertion obviously false",
            "dynamic comparison incomplete",
            "not implemented",
            "division by zero",
            "unconstrained variables",
        ] or
        iteration.c2_ignored_error in [
            "unreachable code",
            "assertion obviously false",
            "dynamic comparison incomplete",
            "not implemented",
            "division by zero",
            "unconstrained variables",
        ]
        for iteration in zokrates_result.iterations
    )

    # Save circuits + artifact bundle if error detected (but skip known errors)
    has_error = any(iteration.error is not None for iteration in zokrates_result.iterations)
    if has_error and not is_known_error and zokrates_result.original_code and zokrates_result.transformed_code:
        save_error_metamorphic_circuit_pair(
            report_dir,
            zokrates_result.original_code,
            zokrates_result.transformed_code,
            working_dir=working_dir,
        )

    data_entries: list[DataEntry] = []
    for idx, iteration in enumerate(zokrates_result.iterations):
        # Skip iterations with known errors
        if iteration.c1_ignored_error in ["unreachable code", "assertion obviously false", "dynamic comparison incomplete", "not implemented", "division by zero", "unconstrained variables"] or \
           iteration.c2_ignored_error in ["unreachable code", "assertion obviously false", "dynamic comparison incomplete", "not implemented", "division by zero", "unconstrained variables"]:
            continue
        
        data_entries.append(
            DataEntry(
                tool="zokrates",
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
                # zokrates-specific fields can be added later (compile/witness/prove times, etc.)
            )
        )

    return TestResult(data_entries)
