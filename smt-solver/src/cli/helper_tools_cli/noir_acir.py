import json
import os
import shutil
import subprocess
from pathlib import Path

from src.backends.noir.acir_to_r1cs import translate_decoded_noir_acir_to_r1cs
from src.cli.helper_tools_cli.translate_dsl import (
	sanitize_noir_package_name,
	translate_smtlib2_to_dsl,
	write_noir_project,
)


def _acir_decoder_paths() -> tuple[Path, Path]:
	root = Path(__file__).resolve().parents[3]
	tool_dir = root / "tools" / "acir-decoder"
	return tool_dir / "Cargo.toml", tool_dir / "target" / "release" / "acir-decoder"


def build_acir_decoder(log=print) -> Path:
	cargo_bin = shutil.which("cargo")
	if cargo_bin is None:
		raise RuntimeError("'cargo' not found in PATH")

	manifest_path, binary_path = _acir_decoder_paths()
	subprocess.run(
		[cargo_bin, "build", "--manifest-path", str(manifest_path), "--release"],
		check=True,
		capture_output=True,
		text=True,
	)
	if not binary_path.exists():
		raise RuntimeError(f"ACIR decoder binary was not produced: {binary_path}")
	log(f"Built ACIR decoder -> {binary_path}")
	return binary_path


def decode_noir_artifact(artifact_path: Path, decoder_bin: Path, log=print) -> Path:
	decoded_path = artifact_path.with_name(f"{artifact_path.name}.decoded.json")
	env = os.environ.copy()
	inspector_bin = shutil.which("noir-inspector")
	if inspector_bin is not None:
		env["NOIR_INSPECTOR_BIN"] = inspector_bin
	subprocess.run(
		[str(decoder_bin), str(artifact_path), "--output", str(decoded_path)],
		check=True,
		capture_output=True,
		text=True,
		env=env,
	)
	log(f"Decoded ACIR artifact {artifact_path} -> {decoded_path}")
	return decoded_path


def emit_sr1cs_from_decoded_noir_artifact(decoded_path: Path, log=print) -> Path:
	sr1cs_path = translate_decoded_noir_acir_to_r1cs(decoded_path)
	log(f"Translated decoded ACIR {decoded_path} -> {sr1cs_path}")
	return sr1cs_path


def compile_smt2_folder_to_noir_acir(
	in_folder: Path,
	out_folder: Path,
	count: int,
	cache_home: Path | None = None,
	decode_bytecode: bool = True,
	log=print,
) -> dict:
	"""Translate SMT-LIB files to Noir and compile them to ACIR JSON artifacts."""
	if count <= 0:
		raise ValueError("--count must be > 0")

	nargo_bin = shutil.which("nargo")
	if nargo_bin is None:
		raise RuntimeError("'nargo' not found in PATH")

	smt2_files = sorted(in_folder.rglob("*.smt2"))
	if not smt2_files:
		raise ValueError(f"No .smt2 files found under {in_folder}")

	selected_files = smt2_files[:count]
	out_folder.mkdir(parents=True, exist_ok=True)
	cache_home = cache_home or (Path("/tmp") / "smt_solver_noir_home")
	cache_home.mkdir(parents=True, exist_ok=True)
	decoder_bin = build_acir_decoder(log=log) if decode_bytecode else None

	results: list[dict[str, str]] = []
	for smt2_file in selected_files:
		relative_parent = smt2_file.parent.relative_to(in_folder)
		project_dir = out_folder / relative_parent / smt2_file.stem
		package_name = sanitize_noir_package_name(smt2_file.stem)

		smtlib2 = smt2_file.read_text()
		noir_source, extension = translate_smtlib2_to_dsl(smtlib2, "noir", output_format="circuzz")
		if extension != ".nr":
			raise RuntimeError(f"Unexpected Noir extension: {extension}")
		write_noir_project(project_dir, package_name, noir_source)
		log(f"Translated {smt2_file} -> {project_dir / 'src' / 'main.nr'}")

		env = os.environ.copy()
		env["HOME"] = str(cache_home)
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
		log(f"Compiled {project_dir} -> {artifact_path}")

		decoded_acir_path = None
		sr1cs_path = None
		if decode_bytecode:
			decoded_acir_path = decode_noir_artifact(artifact_path, decoder_bin=decoder_bin, log=log)
			sr1cs_path = emit_sr1cs_from_decoded_noir_artifact(decoded_acir_path, log=log)

		results.append(
			{
				"input": str(smt2_file),
				"project_dir": str(project_dir),
				"artifact": str(artifact_path),
				"decoded_acir": str(decoded_acir_path) if decoded_acir_path else None,
				"sr1cs": str(sr1cs_path) if sr1cs_path else None,
			}
		)

	summary = {
		"input_root": str(in_folder),
		"output_root": str(out_folder),
		"cache_home": str(cache_home),
		"count": len(results),
		"artifacts": results,
	}
	summary_path = out_folder / "acir_manifest.json"
	summary_path.write_text(json.dumps(summary, indent=2))
	log(f"Wrote ACIR manifest to {summary_path}")
	return summary
