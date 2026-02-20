import io
import re
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from random import Random
from pathlib import Path

from circuzz.ir.config import GeneratorKind
from circuzz.common.field import CurvePrime
from circuzz.common.field import random_field_element
from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.helper import assert_circuit_compatibility
from circuzz.common.filesystem import clean_or_create_dir
from circuzz.common.filesystem import copy_files_to_dir
from circuzz.common.filesystem import get_files_in_dir
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning, TuningStrategy

from .command import go_test
from .utils import random_engine_system_pair
from .utils import IterationSetting
from .utils import curve_to_prime
from .utils import GnarkCurve
from .utils import write_test_func_to_buffer
from .utils import PATH_TO_BASE_PROJECT
from .ir2gnark import IR2GnarkVisitor
from .emitter import EmitVisitor

logger = get_color_logger()

# this might be recoverable
TEST_TIMEOUT_PANIC_STDOUT = "test timed out after"

# this seems like an interesting error that crashes the whole tests
TEST_EXCEPTION_BULK_TOO_BIG_STDERR = "internal compiler error: NewBulk too big:"

class GnarkError(StrEnum):
    METAMORPHIC_TEST_FRAMEWORK_ERROR = "metamorphic violation in test cases"
    UNKNOWN_TEST_FRAMEWORK_ERROR = "unknown test framework error"
    SMT_WITNESS_SOLVE_ERROR = "SMT witness solve error"

@dataclass
class TestIterations():

    c1_compile      : bool | None = None
    c1_compile_time : float | None = None
    c2_compile      : bool | None = None
    c2_compile_time : float | None = None

    c1_new_witness      : bool | None = None
    c1_new_witness_time : float | None = None
    c2_new_witness      : bool | None = None
    c2_new_witness_time : float | None = None

    c1_witness_solved      : bool | None = None
    c1_witness_solved_time : float | None = None
    c2_witness_solved      : bool | None = None
    c2_witness_solved_time : float | None = None

    c1_witness_write      : bool | None = None
    c1_witness_write_time : float | None = None
    c2_witness_write      : bool | None = None
    c2_witness_write_time : float | None = None

    c1_new_srs      : bool | None = None
    c2_new_srs      : bool | None = None

    c1_proof_setup      : bool | None = None
    c1_proof_setup_time : float | None = None
    c2_proof_setup      : bool | None = None
    c2_proof_setup_time : float | None = None

    c1_prove      : bool | None = None
    c1_prove_time : float | None = None
    c2_prove      : bool | None = None
    c2_prove_time : float | None = None

    c1_witness_public      : bool | None = None
    c1_witness_public_time : float | None = None
    c2_witness_public      : bool | None = None
    c2_witness_public_time : float | None = None

    c1_verify      : bool | None = None
    c1_verify_time : float | None = None
    c2_verify      : bool | None = None
    c2_verify_time : float | None = None

    cs_engine    : str | None = None
    proof_system : str | None = None

    error : str | None = None

    go_test_time : float | None = None

    go_timeout : bool = False
    go_ignored_compiler_error : str | None = None

    def is_error(self) -> bool:
        return self.error != None

@dataclass
class GnarkResult():
    iterations : dict[str,list[TestIterations]] = field(default_factory=dict)
    circuit_codes : dict[str, tuple[str, str]] = field(default_factory=dict)  # Maps circuit name to (original_code, transformed_code)


def _compact_error_message(stdout: str, stderr: str, max_len: int = 4000) -> str:
    text = stderr.strip()
    if text == "":
        text = stdout.strip()
    if text == "":
        return "no stdout/stderr captured"
    if len(text) > max_len:
        return text[:max_len] + "\n...[truncated]..."
    return text

def setup_project(test_dir: Path) -> Path:
    """
    Setup a gnark project in the given test directory. The return value
    is the path to a template test file ready to be populated with circuit
    unit tests. The project directory structure looks like the following:

    ```
        <TEST-DIR>
            |____ go.mod
            |____ go.sum
            |____ template_test.go
    ```

    IMPORTANT: This function only works when called inside of the container!
               It relays on an existing project at `/gnark_base_project`.
    """

    # base project with version inside of container
    if not PATH_TO_BASE_PROJECT.is_dir():
        raise RuntimeError(f"unable to find base project {PATH_TO_BASE_PROJECT}! Is it not called from container?")

    logger.info(f"clean or create working-dir: {test_dir}")
    clean_or_create_dir(test_dir)
    files = get_files_in_dir(PATH_TO_BASE_PROJECT)
    copy_files_to_dir(files, test_dir)

    template_test_go = test_dir / "template_test.go"
    if not template_test_go.is_file():
        raise RuntimeError(f"unable to find template file {template_test_go}! Is it not called from container?")

    return template_test_go # return template file

def random_inputs \
    ( inputs: list[str]
    , prime: CurvePrime
    , boundary_prob: float
    , rng: Random
    ) -> dict[str, int]:
    return {sig : random_field_element(prime, rng,
        boundary_prob=boundary_prob) for sig in inputs}

def run_metamorphic_tests \
    ( circuit_pairs : list[tuple[MetamorphicCircuitPair, GnarkCurve]]
    , test_seed : int
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> GnarkResult:

    """
    Generates unit tests of metamorphic circuit pairs for the gnark framework.
    If a metamorphic violation is detected an error string is return, otherwise
    'None' is returned
    """

    # check that only arithmetic generators are used!
    generatorKind = config.ir.generation.generator
    if generatorKind not in [GeneratorKind.ARITHMETIC, GeneratorKind.QUADRATIC]:
        raise NotImplementedError(f"gnark is unable to deal with '{generatorKind}' generator!")

    # sanity checks
    for circuit_pair, _ in circuit_pairs:
        assert_circuit_compatibility([circuit_pair.fst, circuit_pair.snd])

    rng = Random(test_seed)

    logger.info("setup gnark test project")
    template_test_go = setup_project(working_dir)

    buffer = io.StringIO()

    # ----------------------------------------------------------
    # Transform circuits to gnark and write to a string buffer
    # ----------------------------------------------------------

    iteration_marker : dict[str, int] = {}
    gnark_result = GnarkResult()

    for circuit_pair, gnark_curve in circuit_pairs:

        circuit1 = circuit_pair.fst
        circuit2 = circuit_pair.snd
        relation = circuit_pair.kind
        prime = curve_to_prime(gnark_curve)

        c1 = IR2GnarkVisitor().transform(circuit1)
        c2 = IR2GnarkVisitor().transform(circuit2)

        # Store the generated code in the result
        code_buffer_c1 = io.StringIO()
        code_buffer_c2 = io.StringIO()
        emitter = EmitVisitor()
        emitter.emit_to_buffer(code_buffer_c1, c1)
        emitter.emit_to_buffer(code_buffer_c2, c2)
        gnark_result.circuit_codes[circuit1.name] = (code_buffer_c1.getvalue(), code_buffer_c2.getvalue())

        inputs = circuit1.inputs

        boundary_prob = config.gnark.boundary_input_probability
        test_iterations = config.gnark.test_iterations

        # NOTE:
        #       * The time online tuning for gnark does NOT consider iterations separately.
        #         If the tuner would execute proof and verification, it is executed for all
        #         iterations.
        #       * The execution online tuning for gnark only updates AFTER the GNARK executions and
        #         similar to the time online tuning does not consider different iterations due to
        #         the increasing complexity.
        #       * All strategies work by setting a probability for the gnark test file.
        #       * All strategies do not distinguish between bundles and count and apply everything
        #         as if it was a single execution.
        #
        # TODO: This part could be improved by implementing the whole strategy into the go file.
        match online_tuning.prove_and_verify_tuning_strategy:
            case TuningStrategy.NEVER:
                prove_and_verify_percentage = 0
            case TuningStrategy.ALWAYS:
                prove_and_verify_percentage = 1
            case TuningStrategy.TIME:
                prove_and_verify_percentage = 1 if online_tuning.is_prove_and_verify(rng) else 0
            case TuningStrategy.EXECUTION:
                prove_and_verify_percentage = 1 if online_tuning.is_prove_and_verify(rng) else 0
            case TuningStrategy.LIKELIHOOD:
                prove_and_verify_percentage = online_tuning.prove_and_verify_target_percentage
            case _:
                raise NotImplementedError(f"unknown tuning strategy {online_tuning.prove_and_verify_tuning_strategy}")

        iterations = []
        settings: list[IterationSetting] = []
        for _ in range(test_iterations):
            input_map = random_inputs(inputs, prime, boundary_prob, rng)
            engine, system = random_engine_system_pair(rng)
            settings.append(IterationSetting(input_map, engine, prove_and_verify_percentage, system))

            iterations.append(TestIterations(cs_engine=engine.value, proof_system=system.value))

        gnark_result.iterations[circuit1.name] = iterations
        iteration_marker[circuit1.name] = 0

        write_test_func_to_buffer(buffer, c1, c2, relation, gnark_curve, settings)

    # ----------------------------------------------------------
    # Append unit tests from string buffer to template test file
    # ----------------------------------------------------------

    with open(template_test_go, "a") as file_handler:
        file_handler.write("\n")
        file_handler.write(buffer.getvalue())

    # ----------------------------------------------------------
    # Run go test
    # ----------------------------------------------------------

    # run test and parse relevant circuits
    logger.info("start go testing ...")
    test_status = go_test(working_dir, config.gnark.go_test_timeout)
    lines = test_status.stdout.split("\n")

    go_test_time = test_status.delta_time

    # TODO: FIXME: Currently this marks also any finished result and reached state!
    #              This is just a temporary solution to deal with go test timeouts for now.
    is_test_timeout = TEST_TIMEOUT_PANIC_STDOUT in test_status.stdout

    # check for failing compiler error and stop immediately
    if TEST_EXCEPTION_BULK_TOO_BIG_STDERR in test_status.stderr:
        for key in gnark_result.iterations:
            curr_iterations = gnark_result.iterations[key]
            only_iteration = curr_iterations[0]
            only_iteration.go_ignored_compiler_error = "NewBulk too big"
            only_iteration.go_test_time = go_test_time
            gnark_result.iterations[key] = [only_iteration]
        return gnark_result # abort

    # check for any other errors, ignore timeouts
    if test_status.returncode != 0 and not is_test_timeout:
        error_lines = list(filter(lambda x: x.startswith("--- FAIL:"), lines))
        if len(error_lines) == 0:
            logger.critical("Unexpected error in test framework!")
            logger.debug(test_status)
            raise RuntimeError("Unexpected error in test framework!")

    # report panics as they might be interesting
    reported_panics = set()
    for line in lines:
        log_pattern = re.compile(".*Test_(C[1,2]_\d+_\d+): (.+)") # pyright: ignore
        log_match = log_pattern.match(line)
        if log_match and log_match.group(1) and log_match.group(2):
            circuit_name = log_match.group(1)
            log_msg = log_match.group(2)

            # TODO: maybe do something with "start" here
            # TODO: maybe do something with "error: witness mis-matching outputs"

            idx = iteration_marker[circuit_name]
            if "panic" in log_msg:
                if not log_msg in reported_panics:
                    reported_panics.add(log_msg)
                    logger.warning(f"{log_msg}")
            elif "test status:" in log_msg:
                # test ended properly and we can increase input runs
                iteration_marker[circuit_name] += 1
            elif "prove & verify opportunity" in log_msg:
                online_tuning.inc_prove_and_verify_ticks()
            elif "prove & verify => start" in log_msg:
                online_tuning.inc_prove_and_verify_exec()
            else:
                msg_pattern = re.compile("^([^\s]+)( time)? (c[1|2]) => ([^\s]+)$") # pyright: ignore
                msg_match = msg_pattern.match(log_msg)
                if msg_match != None:
                    subject = msg_match.group(1)
                    is_time = msg_match.group(2) != None
                    circuit = msg_match.group(3)
                    value = msg_match.group(4)

                    curr_iteration = gnark_result.iterations[circuit_name][idx]

                    match subject:
                        case "Compile":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_compile_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c1_compile = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_compile_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c2_compile = value == "ok"
                        case "NewWitness":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_new_witness_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c1_new_witness = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_new_witness_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c2_new_witness = value == "ok"
                        case "IsSolved":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_witness_solved_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c1_witness_solved = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_witness_solved_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c2_witness_solved = value == "ok"
                        case "WitnessWriteTo":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_witness_write_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c1_witness_write = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_witness_write_time = float(value)
                                    online_tuning.add_general_execution_time(float(value))
                                else:
                                    curr_iteration.c2_witness_write = value == "ok"
                        case "NewSRS":
                            if circuit == "c1":
                                curr_iteration.c1_new_srs = value == "ok"
                            if circuit == "c2":
                                curr_iteration.c2_new_srs = value == "ok"
                        case "ProofSetup":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_proof_setup_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c1_proof_setup = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_proof_setup_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c2_proof_setup = value == "ok"
                        case "Prove":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_prove_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c1_prove = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_prove_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c2_prove = value == "ok"
                        case "Public":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_witness_public_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c1_witness_public = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_witness_public_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c2_witness_public = value == "ok"
                        case "Verify":
                            if circuit == "c1":
                                if is_time:
                                    curr_iteration.c1_verify_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c1_verify = value == "ok"
                            if circuit == "c2":
                                if is_time:
                                    curr_iteration.c2_verify_time = float(value)
                                    online_tuning.add_prove_or_verify_time(float(value))
                                else:
                                    curr_iteration.c2_verify = value == "ok"

        err_pattern = re.compile("--- FAIL: Test_(C[1,2]_\d+_\d+) ") # pyright: ignore
        err_match = err_pattern.match(line)
        if err_match and err_match.group(1):
            circuit_name = err_match.group(1)
            idx = iteration_marker[circuit_name] - 1 # "-1" is required because of marker increase
            logger.info(f"Test_{circuit_name} failed!")
            gnark_result.iterations[circuit_name][idx].error = GnarkError.METAMORPHIC_TEST_FRAMEWORK_ERROR
            gnark_result.iterations[circuit_name] = gnark_result.iterations[circuit_name][0:idx+1] # remove never executed iterations

        # TODO: FIXME: see comment at "is_test_timeout" definition
        # sets last iterations of every pair to timeout (for now best guess)
        if is_test_timeout:
            for circuit_name in gnark_result.iterations:
                gnark_result.iterations[circuit_name][-1].go_timeout = is_test_timeout

    # update all gnark iterations with go test time
    for c in gnark_result.iterations:
        for i in gnark_result.iterations[c]:
            i.go_test_time = go_test_time

    logger.debug(test_status)
    return gnark_result


def _as_gnark_input(value: int | bool) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def _extract_struct_name_from_source(source: str) -> str:
    match = re.search(r"type\s+([A-Za-z0-9_]+)\s+struct\s*\{", source)
    if match is None:
        raise ValueError("unable to extract circuit struct name from gnark source")
    return match.group(1)


def _extract_input_fields_from_source(source: str) -> list[str]:
    fields = re.findall(r"FVar_([A-Za-z0-9_]+)\s+frontend\.Variable", source)
    return fields


def run_smt_pipeline_tests_from_go_source(
    circuit_name: str,
    go_source: str,
    models: list[dict[str, int | bool]],
    curve: GnarkCurve,
    working_dir: Path,
    config: Config,
    online_tuning: OnlineTuning,
) -> tuple[list[TestIterations], float]:
    template_test_go = setup_project(working_dir)
    struct_name = _extract_struct_name_from_source(go_source)
    inputs = _extract_input_fields_from_source(go_source)
    if len(inputs) == 0:
        raise ValueError("no gnark input fields found in generated source")

    test_name = f"SMT_{circuit_name}".replace("-", "_")
    with open(template_test_go, "a") as file_handler:
        file_handler.write("\n")
        file_handler.write(go_source)
        file_handler.write("\n\n")
        file_handler.write(f"func Test_{test_name}(t *testing.T) {{\n")
        file_handler.write("    t.Parallel()\n")
        file_handler.write(f"    curve := ecc.{curve.value}\n")
        file_handler.write(f"    var c1 {struct_name}\n")
        file_handler.write(f"    var c2 {struct_name}\n")
        file_handler.write("    var co frontend.Circuit = &c2\n")
        file_handler.write(f"    a1 := {struct_name}{{}}\n")
        file_handler.write(f"    a2 := {struct_name}{{}}\n")
        file_handler.write("    type setting struct {\n")
        file_handler.write("        engine csEngine\n")
        file_handler.write("        skipProverPercentage float64\n")
        file_handler.write("        system proofSystem\n")
        for var in inputs:
            file_handler.write(f"        FVar_{var} *big.Int\n")
        file_handler.write("    }\n")
        file_handler.write(f"    var iterSettings [{len(models)}]setting\n")
        for idx, model in enumerate(models):
            # In SMT mode we require full pipeline execution; do not skip prove/verify.
            file_handler.write(f"    iterSettings[{idx}] = setting{{r1csId, 1.0, groth16Id")
            for _ in inputs:
                file_handler.write(", new(big.Int)")
            file_handler.write("}\n")
            for var in inputs:
                if var not in model:
                    raise ValueError(f"model is missing required gnark input '{var}'")
                value = _as_gnark_input(model[var])
                file_handler.write(f"    iterSettings[{idx}].FVar_{var}.SetString(\"{value}\", 10)\n")
        file_handler.write("    for _, s := range iterSettings {\n")
        for var in inputs:
            file_handler.write(f"        a1.FVar_{var} = s.FVar_{var}\n")
            file_handler.write(f"        a2.FVar_{var} = s.FVar_{var}\n")
        file_handler.write(f"        st := cmpCircuits(curve, &c1, co, &a1, &a2, s.skipProverPercentage, s.engine, s.system, \"Test_{test_name}\")\n")
        file_handler.write(f"        log.Printf(\"Test_{test_name}: test status: %v\\n\", st)\n")
        file_handler.write("        if st != eq {\n")
        file_handler.write("            t.Errorf(\"Expected '%v', got '%v'.\", \"eq\", st)\n")
        file_handler.write("            return\n")
        file_handler.write("        }\n")
        file_handler.write("    }\n")
        file_handler.write("}\n")

    test_status = go_test(working_dir, config.gnark.go_test_timeout, verbose=True)
    iterations: list[TestIterations] = []
    for _ in models:
        iterations.append(TestIterations())

    # Parse overall test status as pass/fail per model.
    lines = test_status.stdout.split("\n")
    marker = 0
    for line in lines:
        if f"Test_{test_name}: test status:" in line:
            if marker < len(iterations):
                iterations[marker].go_test_time = test_status.delta_time
                marker += 1
    # SMT oracle is strict: any witness solve error means invalid model replay.
    for idx, line in enumerate(lines):
        if f"Test_{test_name}: IsSolved c1 => err" in line or f"Test_{test_name}: IsSolved c2 => err" in line:
            target_idx = max(0, min(marker, len(iterations) - 1))
            iterations[target_idx].error = GnarkError.SMT_WITNESS_SOLVE_ERROR
            start = max(0, idx - 6)
            end = min(len(lines), idx + 8)
            snippet = "\n".join(lines[start:end])
            iterations[target_idx].go_ignored_compiler_error = _compact_error_message(
                f"detected IsSolved error in SMT replay\n\n{snippet}",
                test_status.stderr,
            )
            return iterations, test_status.delta_time
    if marker != len(iterations):
        idx = min(marker, len(iterations) - 1)
        iterations[idx].error = GnarkError.UNKNOWN_TEST_FRAMEWORK_ERROR
        iterations[idx].go_ignored_compiler_error = _compact_error_message(
            test_status.stdout + f"\n\nmissing status markers: got={marker}, expected={len(iterations)}",
            test_status.stderr,
        )
        return iterations, test_status.delta_time
    is_timeout = TEST_TIMEOUT_PANIC_STDOUT in test_status.stdout
    if is_timeout:
        for i in iterations:
            i.go_timeout = True
    if test_status.returncode != 0:
        idx = min(marker, len(iterations) - 1)
        iterations[idx].error = GnarkError.UNKNOWN_TEST_FRAMEWORK_ERROR
        iterations[idx].go_ignored_compiler_error = _compact_error_message(
            test_status.stdout,
            test_status.stderr,
        )
    return iterations, test_status.delta_time
