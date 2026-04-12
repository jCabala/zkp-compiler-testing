from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from src.cli.solver_cli.circom import smtlib2_to_circom, build_r1cs_from_circom
from src.cli.solver_cli.gnark import smtlib2_to_gnark, build_r1cs_from_gnark
from src.backends.circom.r1cs import OptFlag
from src.r1cs.emit_qf_ff import emit_qf_ff


@dataclass
class BoolToFFConfig:
	dsl: str
	compiler: str | None
	opt_level: str
	suffix: str | None
	skip_existing: bool
	continue_on_error: bool
	with_logs: bool
	keep_intermediate: Path | None
	max_out: int | None


def _log(msg: str, with_logs: bool, log):
	if with_logs:
		log(msg)


def _optflag(opt_level: str) -> OptFlag:
	if opt_level == "O0":
		return OptFlag.O0
	if opt_level == "O1":
		return OptFlag.O1
	if opt_level == "O2":
		return OptFlag.O2
	raise ValueError(f"Unsupported opt level: {opt_level}")


def _write_intermediate(path: Path | None, name: str, content: str) -> Path | None:
	if path is None:
		return None
	path.mkdir(parents=True, exist_ok=True)
	out = path / name
	out.write_text(content)
	return out


def _prepare_r1cs_from_circom(
	smtlib2: str,
	*,
	compiler: str | None,
	opt_level: str,
	with_logs: bool,
	log,
	keep_intermediate: Path | None,
):
	circom_code, bool_vars = smtlib2_to_circom(smtlib2)
	intermediate_name = f"temp-{uuid4()}.circom"
	circom_path = _write_intermediate(keep_intermediate, intermediate_name, circom_code)
	cleanup = False
	if circom_path is None:
		tmp_dir = Path("/tmp/smt_solver")
		tmp_dir.mkdir(parents=True, exist_ok=True)
		circom_path = tmp_dir / intermediate_name
		circom_path.write_text(circom_code)
		cleanup = True

	_log(f"Compiling Circom: {circom_path}", with_logs, log)
	try:
		return build_r1cs_from_circom(
			circom_path,
			bool_vars=tuple(bool_vars),
			opt_level=_optflag(opt_level),
			with_logs=with_logs,
			compiler=compiler or "circom",
			eliminate_removable=False,
			optimize=False,
		)
	finally:
		if cleanup and circom_path.exists():
			circom_path.unlink()


def _prepare_r1cs_from_gnark(
	smtlib2: str,
	*,
	compiler: str | None,
	with_logs: bool,
	log,
	keep_intermediate: Path | None,
):
	gnark_code = smtlib2_to_gnark(smtlib2)
	intermediate_name = f"temp-{uuid4()}.go"
	gnark_path = _write_intermediate(keep_intermediate, intermediate_name, gnark_code)
	cleanup = False
	if gnark_path is None:
		tmp_dir = Path("/tmp/smt_solver")
		tmp_dir.mkdir(parents=True, exist_ok=True)
		gnark_path = tmp_dir / intermediate_name
		gnark_path.write_text(gnark_code)
		cleanup = True

	_log(f"Compiling Gnark: {gnark_path}", with_logs, log)
	try:
		r1cs, _ = build_r1cs_from_gnark(
			gnark_path,
			with_logs=with_logs,
			compiler=compiler or "go",
			eliminate_removable=False,
			optimize=False,
		)
		return r1cs
	finally:
		if cleanup and gnark_path.exists():
			gnark_path.unlink()


def generate_ff_benchmarks(
	*,
	in_folder: Path,
	out_folder: Path,
	dsl: str,
	compiler: str | None,
	max_out: int | None,
	opt_level: str,
	suffix: str | None,
	skip_existing: bool,
	continue_on_error: bool,
	with_logs: bool,
	keep_intermediate: Path | None,
	log=print,
):
	out_folder.mkdir(parents=True, exist_ok=True)
	smt2_files = sorted(in_folder.glob("*.smt2"))
	if not smt2_files:
		log(f"No .smt2 files found in {in_folder}")
		return

	selected = smt2_files[:max_out] if max_out is not None else smt2_files
	converted = 0

	for smt2_path in selected:
		try:
			smtlib2 = smt2_path.read_text()
			if dsl == "circom":
				r1cs = _prepare_r1cs_from_circom(
					smtlib2,
					compiler=compiler,
					opt_level=opt_level,
					with_logs=with_logs,
					log=log,
					keep_intermediate=keep_intermediate,
				)
			elif dsl == "gnark":
				r1cs = _prepare_r1cs_from_gnark(
					smtlib2,
					compiler=compiler,
					with_logs=with_logs,
					log=log,
					keep_intermediate=keep_intermediate,
				)
			else:
				raise ValueError(f"Unsupported DSL: {dsl}")

			out_name = smt2_path.stem
			if suffix:
				out_name = f"{out_name}--{suffix}"
			out_file = out_folder / f"{out_name}.smt2"
			if skip_existing and out_file.exists():
				_log(f"Skipping existing {out_file}", with_logs, log)
				continue

			qf_ff = emit_qf_ff(r1cs, source_path=smt2_path, backend=dsl)
			out_file.write_text(qf_ff)
			converted += 1
			_log(f"Wrote {out_file}", with_logs, log)
		except Exception as e:
			if continue_on_error:
				log(f"Skipping {smt2_path.name}: {e}")
				continue
			raise

	log(f"Converted {converted} file(s) to QF_FF in {out_folder}")
