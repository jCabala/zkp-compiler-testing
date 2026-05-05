import json
import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from src.backends.noir.acir_to_r1cs import build_r1cs_from_decoded_noir_acir
from src.cli.helper_tools_cli.noir_acir import build_acir_decoder, decode_noir_artifact
from src.cli.helper_tools_cli.translate_dsl import (
    sanitize_noir_package_name,
    translate_smtlib2_to_dsl,
    write_noir_project,
)
from src.cli.solver_cli.common import log, run_picus, solution_to_str
from src.r1cs.dump import dump_r1cs as dump_r1cs_text
from src.r1cs.solve import solve_r1cs
from src.r1cs.sr1cs import dump_sr1cs


def smtlib2_to_noir(smtlib2: str, solver: str = "z3") -> str:
    del solver  # Noir translation uses the shared SMT-LIB parser defaults.
    source, extension = translate_smtlib2_to_dsl(smtlib2, "noir")
    if extension != ".nr":
        raise RuntimeError(f"Unexpected Noir extension: {extension}")
    return source


def build_r1cs_from_noir(
    noir_path: Path,
    *,
    with_logs: bool,
    cache_home: Path,
    compiler: str,
) -> tuple:
    nargo_bin = shutil.which(compiler) if Path(compiler).name == compiler else compiler
    if nargo_bin is None:
        raise RuntimeError(f"'{compiler}' not found in PATH")

    source = noir_path.read_text()
    package_name = sanitize_noir_package_name(noir_path.stem)
    project_dir = noir_path.parent / f"{noir_path.stem}_noir_proj"
    write_noir_project(project_dir, package_name, source)

    env = os.environ.copy()
    env["HOME"] = str(cache_home)
    cache_home.mkdir(parents=True, exist_ok=True)

    log(f"Compiling Noir file: {noir_path}...", with_logs=with_logs)
    subprocess.run(
        [nargo_bin, "compile"],
        cwd=project_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    artifact_path = project_dir / "target" / f"{package_name}.json"
    if not artifact_path.exists():
        raise RuntimeError(f"Expected ACIR artifact was not produced: {artifact_path}")

    decoder_bin = build_acir_decoder(log=lambda _msg: None)
    decoded_path = decode_noir_artifact(artifact_path, decoder_bin=decoder_bin, log=lambda _msg: None)
    decoded = json.loads(decoded_path.read_text())
    translation = build_r1cs_from_decoded_noir_acir(decoded)
    sr1cs_str = dump_sr1cs(
        translation.r1cs,
        input_wires=translation.input_wires,
        output_wires=translation.output_wires,
    )
    return translation.r1cs, sr1cs_str


def solve_noir(
    noir_path: Path,
    *,
    with_model: bool,
    with_logs: bool,
    solver: str,
    tmp_dir: Path,
    hint_model: dict | None = None,
    solving_timeout: int | None = None,
    compiler: str = "nargo",
    dump_r1cs: Path | None = None,
) -> str:
    del with_model
    if hint_model:
        log("Ignoring external hint model for Noir backend", with_logs=with_logs)

    cache_home = tmp_dir / "noir_home"
    r1cs, sr1cs_str = build_r1cs_from_noir(
        noir_path,
        with_logs=with_logs,
        cache_home=cache_home,
        compiler=compiler,
    )

    if solver == "picus":
        log("Solving R1CS using Picus...", with_logs)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_sr1cs_path = tmp_dir / f"temp-{uuid4()}.sr1cs"
        try:
            tmp_sr1cs_path.write_text(sr1cs_str)
            return run_picus(tmp_sr1cs_path, hints=None, solving_timeout=solving_timeout)
        finally:
            if tmp_sr1cs_path.exists():
                tmp_sr1cs_path.unlink()

    if dump_r1cs is not None:
        dump_r1cs.write_text(dump_r1cs_text(r1cs))

    log("Solving R1CS using a SMT solver...", with_logs)
    solution = solve_r1cs(r1cs, backend=solver, with_logs=with_logs, solving_timeout=solving_timeout)
    return solution_to_str(solution)
