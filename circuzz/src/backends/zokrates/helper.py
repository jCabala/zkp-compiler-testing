# -----------------------------
# backends/zokrates/helper.py
# -----------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from random import Random
import re

from circuzz.common.command import ExecStatus
from circuzz.common.field import CurvePrime
from circuzz.common.helper import assert_circuit_compatibility, remove_ansi_escape_sequences
from circuzz.common.field import random_field_element
from circuzz.common.filesystem import clean_or_create_dir
from circuzz.common.metamorphism import MetamorphicCircuitPair, MetamorphicKind
from circuzz.ir.config import GeneratorKind
from circuzz.ir.nodes import Circuit
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning
from experiment.config import TuningStrategy  # optional; not required below

from .emitter import EmitVisitor
from .ir2zokrates import IR2ZokratesVisitor

from .command import (
    zokrates_compile,
    zokrates_compute_witness,   # NOTE: no curve arg
    zokrates_setup,
    zokrates_generate_proof,
    zokrates_verify,
)

from .utils import ZokratesCurve

logger = get_color_logger()

# stderr/stdout fragments we treat as "expected" (i.e., not a harness bug)
ZOK_ASSERTION_FAILED = "Assertion failed"
ZOK_FIELD_RANGE = "Field constant not in the representable range"

# quick patterns
_RE_ASSERT_LOC = re.compile(r"Assertion failed.*\((.*):(\d+):(\d+)\)")

# ZoKrates wording varies across versions:
_RE_UNCONSTRAINED = re.compile(
    r"\bfound\s+\d+\s+unconstrain(?:ed|t)\s+variable(?:s)?\b",
    re.IGNORECASE,
)

_RE_FIELD_RANGE = re.compile(r"Field constant not in the representable range", re.IGNORECASE)

_RE_UNREACHABLE_CODE = re.compile(r"entered unreachable code", re.IGNORECASE)

_RE_ASSERTION_FAILED_COMPILE = re.compile(r"Assertion failed", re.IGNORECASE)

_RE_DYNAMIC_COMPARISON = re.compile(r"dynamic comparison is incomplete", re.IGNORECASE)

_RE_NOT_IMPLEMENTED = re.compile(r"not implemented", re.IGNORECASE)

_RE_DIVISION_BY_ZERO = re.compile(r"division by zero detected", re.IGNORECASE)


class ZokratesError(StrEnum):
    UNKNOWN_COMPILATION_ERROR = "unknown compilation error"
    UNKNOWN_WITNESS_ERROR = "unknown witness error"
    UNKNOWN_PROOF_ERROR = "unknown proof error"
    UNKNOWN_VERIFICATION_ERROR = "unknown verification error"

    METAMORPHIC_VIOLATION_EXECUTION = "metamorphic violated execution"
    METAMORPHIC_VIOLATION_PROOF = "metamorphic violation proof"
    METAMORPHIC_VIOLATION_VERIFICATION = "metamorphic violation verification"

    UNCONSTRAINED_VARIABLES = "unconstrained variables"
    FIELD_CONSTANT_OUT_OF_RANGE = "field constant out of range"
    ASSERTION_FAILED = "assertion failed"
    UNREACHABLE_CODE = "unreachable code"
    ASSERTION_OBVIOUSLY_FALSE = "assertion obviously false"
    DYNAMIC_COMPARISON_INCOMPLETE = "dynamic comparison incomplete"
    NOT_IMPLEMENTED = "not implemented"
    DIVISION_BY_ZERO = "division by zero"


@dataclass
class TestIteration:
    c1_compile: bool | None = None
    c1_compile_time: float | None = None
    c2_compile: bool | None = None
    c2_compile_time: float | None = None

    c1_witness: bool | None = None
    c1_witness_time: float | None = None
    c2_witness: bool | None = None
    c2_witness_time: float | None = None

    c1_setup: bool | None = None
    c1_setup_time: float | None = None
    c2_setup: bool | None = None
    c2_setup_time: float | None = None

    c1_prove: bool | None = None
    c1_prove_time: float | None = None
    c2_prove: bool | None = None
    c2_prove_time: float | None = None

    c1_verify: bool | None = None
    c1_verify_time: float | None = None
    c2_verify: bool | None = None
    c2_verify_time: float | None = None

    # "expected"/classified errors (used when we continue rather than fail the test)
    c1_ignored_error: str | None = None
    c2_ignored_error: str | None = None

    # harness-level failure category (stop + archive)
    error: str | None = None

    def is_error(self) -> bool:
        return self.error is not None


@dataclass
class ZokratesResult:
    iterations: list[TestIteration] = field(default_factory=list)
    original_code: str | None = None
    transformed_code: str | None = None


# ================================================================
#                           Parsing
# ================================================================

def _combined_output(status: ExecStatus) -> str:
    """
    ZoKrates sometimes prints important diagnostics to stdout (not only stderr).
    For classification, inspect both.
    """
    return remove_ansi_escape_sequences((status.stderr or "") + "\n" + (status.stdout or ""))


def classify_zokrates_error(status: ExecStatus) -> ZokratesError | None:
    out = _combined_output(status)

    if _RE_UNREACHABLE_CODE.search(out):
        return ZokratesError.UNREACHABLE_CODE
    if _RE_DYNAMIC_COMPARISON.search(out):
        return ZokratesError.DYNAMIC_COMPARISON_INCOMPLETE
    if _RE_NOT_IMPLEMENTED.search(out):
        return ZokratesError.NOT_IMPLEMENTED
    if _RE_DIVISION_BY_ZERO.search(out):
        return ZokratesError.DIVISION_BY_ZERO
    if _RE_ASSERTION_FAILED_COMPILE.search(out):
        return ZokratesError.ASSERTION_OBVIOUSLY_FALSE
    if ZOK_ASSERTION_FAILED in out:
        return ZokratesError.ASSERTION_FAILED
    if _RE_UNCONSTRAINED.search(out):
        return ZokratesError.UNCONSTRAINED_VARIABLES
    if _RE_FIELD_RANGE.search(out) or ZOK_FIELD_RANGE in out:
        return ZokratesError.FIELD_CONSTANT_OUT_OF_RANGE

    return None


def extract_assertion_location(output: str) -> tuple[str, int, int] | None:
    """
    Extract (basename, line, col) so origin/transformed absolute paths don't cause false mismatches.
    """
    m = _RE_ASSERT_LOC.search(output)
    if not m:
        return None
    file_path = m.group(1)
    line = int(m.group(2))
    col = int(m.group(3))
    return (Path(file_path).name, line, col)


# ================================================================
#                           Inputs
# ================================================================

def random_input_args(
    input_signals: list[str],
    curve: CurvePrime,
    boundary_probability: float,
    rng: Random,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for var in input_signals:
        val = random_field_element(curve, rng, exclude_prime=True, boundary_prob=boundary_probability)
        out[var] = str(val)
    return out


def input_args_in_order(input_signals: list[str], input_map: dict[str, str]) -> list[str]:
    return [input_map[name] for name in input_signals]


# ================================================================
#                  IR to ZoKrates and File Setup
# ================================================================

def prepare_program(root: Path, prefix: str, circuit: Circuit) -> tuple[Path, str]:
    working_dir = root / prefix
    clean_or_create_dir(working_dir)
    clean_or_create_dir(working_dir / "out")

    with open(working_dir / "circuit.txt", "w", encoding="utf-8", errors="replace") as f:
        f.write(str(circuit))

    zok_ast = IR2ZokratesVisitor().transform(circuit)
    zok_source = EmitVisitor().emit(zok_ast)

    with open(working_dir / "circuit.zok", "w", encoding="utf-8", errors="replace") as f:
        f.write(zok_source)

    return working_dir, zok_source


# ================================================================
#                     Metamorphic checking
# ================================================================

def analyze_metamorphic_relation(
    c1: ExecStatus,
    c2: ExecStatus,
    kind: MetamorphicKind,
) -> ZokratesError | None:
    """
    Stage-local metamorphic rules.

    WEAKER:
      - Only violation: original succeeds AND transformed fails.
      - If both fail => NOT a violation.
      - If transformed succeeds => OK.

    EQUAL:
      - Violation if returncodes differ.
      - If both succeed: optional stdout equality check (kept).
      - If both fail: if both sides are classified, compare class (+ normalized assertion location).
        If classification is unavailable on either side, conservatively accept (not a violation).
    """
    c1_out = _combined_output(c1)
    c2_out = _combined_output(c2)

    c1_err = classify_zokrates_error(c1)
    c2_err = classify_zokrates_error(c2)

    loc1 = extract_assertion_location(c1_out) if c1_err == ZokratesError.ASSERTION_FAILED else None
    loc2 = extract_assertion_location(c2_out) if c2_err == ZokratesError.ASSERTION_FAILED else None

    match kind:
        case MetamorphicKind.WEAKER:
            if c2.returncode == 0:
                return None
            if c1.returncode != 0:
                return None
            return ZokratesError.METAMORPHIC_VIOLATION_EXECUTION

        case MetamorphicKind.EQUAL:
            if c1.returncode != c2.returncode:
                return ZokratesError.METAMORPHIC_VIOLATION_EXECUTION

            if c1.returncode == 0 and c2.returncode == 0:
                if c1.stdout != c2.stdout:
                    return ZokratesError.METAMORPHIC_VIOLATION_EXECUTION
                return None

            # both fail
            if c1_err is not None and c2_err is not None:
                if c1_err != c2_err:
                    return ZokratesError.METAMORPHIC_VIOLATION_EXECUTION
                if (loc1 is not None or loc2 is not None) and loc1 != loc2:
                    return ZokratesError.METAMORPHIC_VIOLATION_EXECUTION
                return None

            return None

    return None


# ================================================================
#                         Curve conversion
# ================================================================

def _to_zokrates_curve(curve: CurvePrime) -> ZokratesCurve:
    match curve:
        case CurvePrime.BN254:
            return ZokratesCurve.BN254
        case CurvePrime.BLS12_381:
            return ZokratesCurve.BLS12_381
        case _:
            raise NotImplementedError(f"ZoKrates backend does not support curve {curve}")


# ================================================================
#                          Testing
# ================================================================

def run_metamorphic_tests(
    metamorphic_pair: MetamorphicCircuitPair,
    seed: int,
    curve: CurvePrime,
    working_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> ZokratesResult:
    """
    Runs ZoKrates compile + witness on a metamorphic circuit pair.
    Optionally setup/prove/verify if enabled in config.

    IMPORTANT POLICY:
      - Compilation + witness: "both fail" is acceptable (not a metamorphic violation).
        We only stop for:
          * WEAKER: original succeeds but transformed fails (real violation)
          * EQUAL: returncode mismatch (real violation)
          * unknown error when ONLY ONE side fails (likely harness/real issue)
      - Setup/prove/verify: if reached, failures are treated as hard errors.
    """
    generator_kind = config.ir.generation.generator
    if generator_kind not in [GeneratorKind.ARITHMETIC, GeneratorKind.QUADRATIC]:
        raise NotImplementedError(
            f"zokrates helper currently expects arithmetic-ish generators, got {generator_kind}"
        )

    assert_circuit_compatibility([metamorphic_pair.fst, metamorphic_pair.snd])

    rng = Random(seed)

    kind = metamorphic_pair.kind
    c1 = metamorphic_pair.fst
    c2 = metamorphic_pair.snd
    input_signals = c1.inputs[::]

    clean_or_create_dir(working_dir)
    logger.info(f"cleaning working dir: {working_dir}")

    proj1, code1 = prepare_program(working_dir, "origin", c1)
    proj2, code2 = prepare_program(working_dir, "transformed", c2)

    result = ZokratesResult(original_code=code1, transformed_code=code2)

    zcurve = _to_zokrates_curve(curve)
    OUT_NAME = "circuit"

    do_proof = bool(getattr(getattr(config, "zokrates", None), "prove_and_verify", False))

    for _ in range(config.zokrates.test_iterations):
        it = TestIteration()
        result.iterations.append(it)

        input_map = random_input_args(
            input_signals, curve, config.zokrates.boundary_input_probability, rng
        )
        args = input_args_in_order(input_signals, input_map)

        # -----------------
        # compile
        # -----------------
        c1_compile = zokrates_compile(
            workdir=proj1,
            source=proj1 / "circuit.zok",
            curve=zcurve,
            out_name=OUT_NAME,
        )
        c2_compile = zokrates_compile(
            workdir=proj2,
            source=proj2 / "circuit.zok",
            curve=zcurve,
            out_name=OUT_NAME,
        )

        online_tuning.add_general_execution_time(c1_compile.delta_time)
        online_tuning.add_general_execution_time(c2_compile.delta_time)

        it.c1_compile = (c1_compile.returncode == 0)
        it.c1_compile_time = c1_compile.delta_time
        it.c2_compile = (c2_compile.returncode == 0)
        it.c2_compile_time = c2_compile.delta_time

        if c1_compile.returncode != 0 or c2_compile.returncode != 0:
            e1 = classify_zokrates_error(c1_compile)
            e2 = classify_zokrates_error(c2_compile)

            if e1 is not None and c1_compile.returncode != 0:
                it.c1_ignored_error = e1.value
            if e2 is not None and c2_compile.returncode != 0:
                it.c2_ignored_error = e2.value

            # If BOTH failed at compilation: acceptable; just check for true metamorphic violation.
            if c1_compile.returncode != 0 and c2_compile.returncode != 0:
                if rel_err := analyze_metamorphic_relation(c1_compile, c2_compile, kind):
                    it.error = rel_err
                    return result
                continue

            # Only one side failed: unknown is actionable
            if c1_compile.returncode != 0 and e1 is None:
                it.error = ZokratesError.UNKNOWN_COMPILATION_ERROR
                return result
            if c2_compile.returncode != 0 and e2 is None:
                it.error = ZokratesError.UNKNOWN_COMPILATION_ERROR
                return result

            if rel_err := analyze_metamorphic_relation(c1_compile, c2_compile, kind):
                it.error = rel_err
                return result

            continue

        # -----------------
        # witness (no curve arg)
        # -----------------
        c1_wit = zokrates_compute_witness(
            workdir=proj1,
            out_name=OUT_NAME,
            args=args,
        )
        c2_wit = zokrates_compute_witness(
            workdir=proj2,
            out_name=OUT_NAME,
            args=args,
        )

        online_tuning.add_general_execution_time(c1_wit.delta_time)
        online_tuning.add_general_execution_time(c2_wit.delta_time)

        it.c1_witness = (c1_wit.returncode == 0)
        it.c1_witness_time = c1_wit.delta_time
        it.c2_witness = (c2_wit.returncode == 0)
        it.c2_witness_time = c2_wit.delta_time

        if c1_wit.returncode != 0 or c2_wit.returncode != 0:
            e1 = classify_zokrates_error(c1_wit)
            e2 = classify_zokrates_error(c2_wit)

            if e1 is not None and c1_wit.returncode != 0:
                it.c1_ignored_error = e1.value
            if e2 is not None and c2_wit.returncode != 0:
                it.c2_ignored_error = e2.value

            # If BOTH failed at witness: acceptable; just check for true metamorphic violation.
            if c1_wit.returncode != 0 and c2_wit.returncode != 0:
                if rel_err := analyze_metamorphic_relation(c1_wit, c2_wit, kind):
                    it.error = rel_err
                    return result
                continue

            # Only one side failed: unknown is actionable
            if c1_wit.returncode != 0 and e1 is None:
                it.error = ZokratesError.UNKNOWN_WITNESS_ERROR
                return result
            if c2_wit.returncode != 0 and e2 is None:
                it.error = ZokratesError.UNKNOWN_WITNESS_ERROR
                return result

            if rel_err := analyze_metamorphic_relation(c1_wit, c2_wit, kind):
                it.error = rel_err
                return result

            continue

        # -----------------
        # optional proof/verify (strict once reached)
        # -----------------
        if do_proof:
            online_tuning.inc_prove_and_verify_ticks()
            if online_tuning.is_prove_and_verify(rng):
                online_tuning.inc_prove_and_verify_exec()

                s1 = zokrates_setup(workdir=proj1, out_name=OUT_NAME, curve=zcurve)
                s2 = zokrates_setup(workdir=proj2, out_name=OUT_NAME, curve=zcurve)
                it.c1_setup = (s1.returncode == 0)
                it.c1_setup_time = s1.delta_time
                it.c2_setup = (s2.returncode == 0)
                it.c2_setup_time = s2.delta_time
                if s1.returncode != 0 or s2.returncode != 0:
                    it.error = ZokratesError.UNKNOWN_PROOF_ERROR
                    return result

                p1 = zokrates_generate_proof(workdir=proj1, out_name=OUT_NAME, curve=zcurve)
                p2 = zokrates_generate_proof(workdir=proj2, out_name=OUT_NAME, curve=zcurve)
                it.c1_prove = (p1.returncode == 0)
                it.c1_prove_time = p1.delta_time
                it.c2_prove = (p2.returncode == 0)
                it.c2_prove_time = p2.delta_time
                if p1.returncode != 0 or p2.returncode != 0:
                    it.error = ZokratesError.UNKNOWN_PROOF_ERROR
                    return result

                v1 = zokrates_verify(workdir=proj1, curve=zcurve)
                v2 = zokrates_verify(workdir=proj2, curve=zcurve)
                it.c1_verify = (v1.returncode == 0)
                it.c1_verify_time = v1.delta_time
                it.c2_verify = (v2.returncode == 0)
                it.c2_verify_time = v2.delta_time
                if v1.returncode != 0 or v2.returncode != 0:
                    it.error = ZokratesError.UNKNOWN_VERIFICATION_ERROR
                    return result

    return result
