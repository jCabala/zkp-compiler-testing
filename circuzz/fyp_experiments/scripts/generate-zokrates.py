#!/usr/bin/env python3
"""
Script to generate ZoKrates programs using arithmetic and boolean generators and (optionally)
test ZoKrates compilation + witness generation.

Changes vs your version:
- NO TRUNCATION of ZoKrates compiler/witness errors (prints full stdout+stderr)
- Saves full logs to programs-zokrates/out/<stem>/{compile.log,witness.log}
- On failure, prints the LAST ~60 lines (usually where the real error is)
- Also prints the FIRST ~20 lines (often contains location header)
- Keeps a concise summary at the end

Usage:
    python generate-zokrates.py                 # Generate + compile + witness
    python generate-zokrates.py --no-check      # Generate only, skip ZoKrates checks
    python generate-zokrates.py -n 20           # Generate 20 per generator
"""

import sys
import subprocess
import argparse
from pathlib import Path
from random import Random

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from circuzz.ir.config import GeneratorKind, IRConfig

# Assumes you added your ZoKrates backend as discussed:
from backends.zokrates.ir2zokrates import IR2ZokratesVisitor
from backends.zokrates.emitter import EmitVisitor


def create_arithmetic_config() -> IRConfig:
    """Create the configuration for the arithmetic generator."""
    return IRConfig.from_dict({
        "rewrite": {
            "weakening_probability": 0,
            "min_rewrites": 0,
            "max_rewrites": 0,
            "rules": {"equivalence": [], "weakening": []}
        },
        "generation": {
            "generator": GeneratorKind.ARITHMETIC,

            "constant_probability_weight": 1,
            "variable_probability_weight": 1,
            "unary_probability_weight": 1,
            "binary_probability_weight": 1,
            "relation_probability_weight": 1,
            "ternary_probability_weight": 1,

            "max_expression_depth": 2,
            "min_number_of_assertions": 1,
            "max_number_of_assertions": 3,
            "min_number_of_input_variables": 2,
            "max_number_of_input_variables": 5,
            "min_number_of_output_variables": 1,
            "max_number_of_output_variables": 3,

            "max_exponent_value": 4,
            "boundary_value_probability": 0.25
        },
        "operators": {
            "relations": ["==", "!="],
            "boolean_unary_operators": ["!"],
            "boolean_binary_operators": ["&&", "||"],
            "arithmetic_unary_operators": ["-"],
            "arithmetic_binary_operators": ["+", "-", "*", "/"],

            "is_arithmetic_ternary_supported": True,
            "is_boolean_ternary_supported": False
        }
    })


def create_boolean_config() -> IRConfig:
    """Create the configuration for the boolean generator."""
    return IRConfig.from_dict({
        "rewrite": {
            "weakening_probability": 0,
            "min_rewrites": 0,
            "max_rewrites": 0,
            "rules": {"equivalence": [], "weakening": []}
        },
        "generation": {
            "generator": GeneratorKind.BOOLEAN,

            "constant_probability_weight": 1,
            "variable_probability_weight": 1,
            "unary_probability_weight": 1,
            "binary_probability_weight": 1,
            "relation_probability_weight": 1,
            "ternary_probability_weight": 1,

            "max_expression_depth": 2,
            "min_number_of_assertions": 1,
            "max_number_of_assertions": 3,
            "min_number_of_input_variables": 2,
            "max_number_of_input_variables": 5,
            "min_number_of_output_variables": 1,
            "max_number_of_output_variables": 3,

            "max_exponent_value": 4,
            "boundary_value_probability": 0.25
        },
        "operators": {
            "relations": ["==", "!="],
            "boolean_unary_operators": ["!"],
            "boolean_binary_operators": ["&&", "||"],
            "arithmetic_unary_operators": ["-"],
            "arithmetic_binary_operators": ["+", "-", "*", "/"],

            "is_arithmetic_ternary_supported": False,
            "is_boolean_ternary_supported": True
        }
    })


def generate_program(seed: int, config: IRConfig, bool_as_field: bool = True):
    """
    Generate a single ZoKrates program using the specified generator.
    """
    circuit = generate_random_circuit(CurvePrime.BN254, False, config, seed)

    # If you have a flag in the visitor, wire it here; otherwise keep as-is.
    # zok_ast = IR2ZokratesVisitor(bool_as_field=bool_as_field).transform(circuit)
    zok_ast = IR2ZokratesVisitor(prime=CurvePrime.BN254).transform(circuit)

    zok_code = EmitVisitor().emit(zok_ast)
    return circuit, zok_code


def _run(cmd: list[str], cwd: Path, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def _preview_output(full: str, head_lines: int = 20, tail_lines: int = 60) -> str:
    """
    Return a helpful preview (head + tail) from a long compiler output.
    """
    lines = full.splitlines()
    if not lines:
        return "<empty output>"

    head = lines[:head_lines]
    tail = lines[-tail_lines:] if len(lines) > tail_lines else []

    if tail:
        return (
            "----[ ZoKrates output (head) ]--------------------------------\n"
            + "\n".join(head)
            + "\n----[ ZoKrates output (tail) ]--------------------------------\n"
            + "\n".join(tail)
        )
    else:
        return (
            "----[ ZoKrates output ]---------------------------------------\n"
            + "\n".join(lines)
        )


def zokrates_compile_and_witness(
    output_dir: Path,
    source_file: Path,
    witness_args: list[int],
    curve: str = "bn128",
) -> tuple[bool, str]:
    """
    Compile a .zok file and compute a witness (best-effort).
    Returns (ok, message). Stores artifacts next to the file in ./out/<stem>/.
    """
    stem = source_file.stem
    out_dir = output_dir / "out" / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "out"
    witness_file = out_dir / "witness"
    compile_log = out_dir / "compile.log"
    witness_log = out_dir / "witness.log"

    # Compile
    c = _run(
        ["zokrates", "compile", "-i", str(source_file), "-o", str(out_file), "--curve", curve],
        cwd=output_dir,
        timeout=60,
    )
    c_full = (c.stdout or "") + ("\n" if c.stdout and c.stderr else "") + (c.stderr or "")
    _write_text(compile_log, c_full)

    if c.returncode != 0:
        preview = _preview_output(c_full)
        return False, (
            f"compile failed (see {compile_log})\n"
            f"{preview}"
        )

    # Witness
    args = [str(v) for v in witness_args]
    w = _run(
        ["zokrates", "compute-witness", "-i", str(out_file), "-o", str(witness_file), "-a", *args],
        cwd=output_dir,
        timeout=60,
    )
    w_full = (w.stdout or "") + ("\n" if w.stdout and w.stderr else "") + (w.stderr or "")
    _write_text(witness_log, w_full)

    if w.returncode != 0:
        preview = _preview_output(w_full)
        return False, (
            f"witness failed (see {witness_log})\n"
            f"{preview}"
        )

    return True, "ok"


def main():
    parser = argparse.ArgumentParser(description="Generate ZoKrates circuits from IR")
    parser.add_argument("--no-check", action="store_true", help="Skip ZoKrates compilation/witness checks")
    parser.add_argument("-n", "--num-programs", type=int, default=5, help="Number of programs per generator (default: 5)")
    parser.add_argument("--curve", type=str, default="bn128", help="ZoKrates curve name (default: bn128)")
    args = parser.parse_args()

    num_arithmetic_programs = args.num_programs
    num_boolean_programs = args.num_programs
    base_seed = 42
    output_dir = Path(__file__).parent / "programs-zokrates"

    output_dir.mkdir(exist_ok=True)

    arithmetic_config = create_arithmetic_config()
    boolean_config = create_boolean_config()

    print()
    print(f"Generating {num_arithmetic_programs} arithmetic and {num_boolean_programs} boolean ZoKrates programs...")
    print(f"Output directory: {output_dir}")
    print()

    rng = Random(base_seed)
    generated_files: list[Path] = []
    total_programs = num_arithmetic_programs + num_boolean_programs
    program_count = 0

    # Generate arithmetic programs
    print("=" * 60)
    print("Arithmetic Generator")
    print("=" * 60)
    for _ in range(num_arithmetic_programs):
        seed = rng.randint(1000000, 9999999)
        program_count += 1

        try:
            circuit_ir, zok_code = generate_program(seed, arithmetic_config, bool_as_field=True)

            output_file = output_dir / f"arithmetic_circuit_{seed}.zok"
            output_file.write_text(zok_code, encoding="utf-8")

            print(f"[{program_count:2d}/{total_programs}] Generated arithmetic_circuit_{seed} (seed: {seed})")
            print(f"                    Inputs: {len(circuit_ir.inputs)}, "
                  f"Outputs: {len(circuit_ir.outputs)}, "
                  f"Assignments: {len(circuit_ir.assignments())}")

            generated_files.append(output_file)

        except Exception as e:
            print(f"[{program_count:2d}/{total_programs}] Error generating program with seed {seed}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print()

    # Generate boolean programs
    print("=" * 60)
    print("Boolean Generator")
    print("=" * 60)
    for _ in range(num_boolean_programs):
        seed = rng.randint(1000000, 9999999)
        program_count += 1

        try:
            circuit_ir, zok_code = generate_program(seed, boolean_config, bool_as_field=True)

            output_file = output_dir / f"boolean_circuit_{seed}.zok"
            output_file.write_text(zok_code, encoding="utf-8")

            print(f"[{program_count:2d}/{total_programs}] Generated boolean_circuit_{seed} (seed: {seed})")
            print(f"                  Inputs: {len(circuit_ir.inputs)}, "
                  f"Outputs: {len(circuit_ir.outputs)}, "
                  f"Assignments: {len(circuit_ir.assignments())}")

            generated_files.append(output_file)

        except Exception as e:
            print(f"[{program_count:2d}/{total_programs}] Error generating program with seed {seed}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print()
    print(f"Successfully generated {len(generated_files)} programs in {output_dir}")
    print()

    if args.no_check:
        print("Skipping ZoKrates checks (--no-check flag set)")
        return

    # Check zokrates exists
    try:
        v = _run(["zokrates", "--version"], cwd=output_dir, timeout=10)
        if v.returncode != 0:
            print("Warning: `zokrates --version` failed. Is ZoKrates installed in PATH?")
            print(_preview_output((v.stdout or "") + "\n" + (v.stderr or ""), head_lines=20, tail_lines=40))
            print("Skipping compilation/witness checks.")
            return
        else:
            print(f"ZoKrates detected: {v.stdout.strip()}")
    except Exception as e:
        print(f"Warning: could not run ZoKrates: {e}")
        print("Skipping compilation/witness checks.")
        return

    print()
    print("Step 1: ZoKrates compile + compute-witness...")

    passed: list[Path] = []
    failed: list[tuple[Path, str]] = []

    # Parse main params to decide witness arity
    import re
    param_re = re.compile(r"def\s+main\s*\((.*?)\)")

    for f in generated_files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            m = param_re.search(src)
            if not m:
                msg = "could not parse main() params"
                failed.append((f, msg))
                print(f"  ✗ {f.name} ({msg})")
                continue

            params_str = m.group(1).strip()
            params = []
            if params_str:
                for part in params_str.split(","):
                    part = part.strip()
                    toks = [t for t in part.split(" ") if t]
                    # last token should be var name
                    if len(toks) >= 1:
                        params.append(toks[-1])

            witness_vals = [1 for _ in params]

            ok, msg = zokrates_compile_and_witness(
                output_dir=output_dir,
                source_file=f,
                witness_args=witness_vals,
                curve=args.curve,
            )

            if ok:
                print(f"  ✓ {f.name}")
                passed.append(f)
            else:
                print(f"  ✗ {f.name}")
                print(msg)  # FULL (but formatted as head+tail)
                failed.append((f, msg))

        except subprocess.TimeoutExpired:
            msg = "timeout"
            print(f"  ⏱ {f.name} ({msg})")
            failed.append((f, msg))
        except Exception as e:
            msg = str(e)
            print(f"  ✗ {f.name}: {msg}")
            failed.append((f, msg))

    print()
    print(f"ZoKrates summary: {len(passed)}/{len(generated_files)} passed compile+witness")
    if failed:
        print("Failed files (first 20):")
        for f, _ in failed[:20]:
            logdir = output_dir / "out" / f.stem
            clog = logdir / "compile.log"
            wlog = logdir / "witness.log"
            print(f"  - {f.name} (logs: {clog} / {wlog})")

    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Generated:      {len(generated_files)} programs")
    print(f"ZoKrates pass:  {len(passed)}/{len(generated_files)}")
    print(f"ZoKrates fail:  {len(failed)}/{len(generated_files)}")


if __name__ == "__main__":
    main()
