import re
from random import Random
from pathlib import Path
from src.smt_lib.zk_ir import Circuit
from src.backends.circom.emitter import EmitVisitor as CircomEmitter
from src.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from src.smt_lib.smt_lib_parser import parse_smtlib2
from src.backends.gnark.ir2gnark import IR2GnarkVisitor
from src.backends.gnark.emitter import EmitVisitor as GnarkEmitter
from src.backends.noir.ir2noir import IR2NoirVisitor
from src.backends.noir.emitter import EmitVisitor as NoirEmitter
from src.cli.solver_cli.zokrates import smtlib2_to_zokrates


def _extract_gnark_fragment_for_circuzz(go_source: str) -> str:
	start_idx = go_source.find("\ntype ")
	if start_idx == -1:
		start_idx = go_source.find("type ")
	if start_idx == -1:
		raise ValueError("Unable to locate Gnark type definition in generated source")

	end_idx = go_source.find("\nfunc main()")
	if end_idx == -1:
		raise ValueError("Unable to locate Gnark main() in generated source")

	fragment = go_source[start_idx:end_idx].strip()
	return fragment + "\n"


def sanitize_noir_package_name(name: str) -> str:
	cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
	if not cleaned:
		cleaned = "noir_case"
	if cleaned[0].isdigit():
		cleaned = f"p_{cleaned}"
	return cleaned.lower()


def write_noir_project(project_dir: Path, package_name: str, main_nr_source: str):
	src_dir = project_dir / "src"
	src_dir.mkdir(parents=True, exist_ok=True)
	(src_dir / "main.nr").write_text(main_nr_source)

	nargo_toml = project_dir / "Nargo.toml"
	nargo_toml.write_text(
		"\n".join(
			[
				"[package]",
				f'name = "{package_name}"',
				'type = "bin"',
				'authors = [""]',
				"",
				"[dependencies]",
				"",
			]
		)
	)


def translate_smtlib2_to_dsl(smtlib2: str, dsl: str, output_format: str = "standalone") -> tuple[str, str]:
	"""
	Translate an SMT-LIB v2 formula to a target DSL.

	Returns (source_code, file_extension).
	"""
	circuit_ir: Circuit = parse_smtlib2(smtlib2)

	if dsl == "circom":
		rng = Random(0)
		ir2circom_visitor = IR2CircomVisitorConstrainAssertions(
			constraint_assignment_probability=1,
			rng=rng,
		)
		circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)
		emitter = CircomEmitter()
		circom_source = emitter.emit(circom_ir)
		if output_format == "circuzz":
			circom_source = circom_source.replace("../circomlib/", "")
		return circom_source, ".circom"

	if dsl == "gnark":
		ir2gnark_visitor = IR2GnarkVisitor(circuzz_compat=(output_format == "circuzz"))
		gnark_ir = ir2gnark_visitor.visit_circuit(circuit_ir)
		emitter = GnarkEmitter()
		gnark_source = emitter.emit(gnark_ir)
		if output_format == "circuzz":
			return _extract_gnark_fragment_for_circuzz(gnark_source), ".go"
		return gnark_source, ".go"

	if dsl == "noir":
		ir2noir_visitor = IR2NoirVisitor()
		noir_ast = ir2noir_visitor.visit_circuit(circuit_ir)
		emitter = NoirEmitter()
		return emitter.emit(noir_ast), ".nr"

	if dsl == "zokrates":
		source, _ = smtlib2_to_zokrates(smtlib2)
		return source, ".zok"

	raise ValueError(f"Unsupported DSL: {dsl}")


def translate_smtlib2_folder(in_folder: Path, out_folder: Path, dsl: str, max_out: int | None = None, output_format: str = "standalone", log=print):
	"""Translate all .smt2 files in a folder to the target DSL."""
	out_folder.mkdir(parents=True, exist_ok=True)
	smt2_files = list(in_folder.glob("*.smt2"))
	if not smt2_files:
		log(f"No .smt2 files found in {in_folder}")
		return

	selected_files = smt2_files[:max_out] if max_out is not None else smt2_files
	converted_count = 0
	for smt2_file in selected_files:
		smtlib2 = smt2_file.read_text()
		dsl_code, extension = translate_smtlib2_to_dsl(smtlib2, dsl, output_format=output_format)
		if output_format == "circuzz" and dsl == "noir":
			project_dir = out_folder / smt2_file.stem
			package_name = sanitize_noir_package_name(smt2_file.stem)
			write_noir_project(project_dir, package_name, dsl_code)
			out_file = project_dir / "src" / "main.nr"
		else:
			out_file = out_folder / f"{smt2_file.stem}{extension}"
			out_file.write_text(dsl_code)
		log(f"Translating {smt2_file} -> {out_file}")
		converted_count += 1

	log(f"Converted {converted_count} files to {dsl} ({output_format}) in {out_folder}")
