from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from src.cli.solver_cli.circom import smtlib2_to_circom, build_r1cs_from_circom
from src.cli.solver_cli.gnark import smtlib2_to_gnark, build_r1cs_from_gnark
from src.cli.solver_cli.zokrates import smtlib2_to_zokrates
from src.backends.circom.r1cs import OptFlag
from src.backends.zokrates.r1cs import compile_to_r1cs as compile_zokrates_to_r1cs, parse_r1cs as parse_zokrates_r1cs
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
	max_vars: int | None = None


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


def _prepare_r1cs_from_zokrates(
	smtlib2: str,
	*,
	compiler: str | None,
	with_logs: bool,
	log,
	keep_intermediate: Path | None,
):
	zokrates_code, _ = smtlib2_to_zokrates(smtlib2)
	intermediate_name = f"temp-{uuid4()}.zok"
	zokrates_path = _write_intermediate(keep_intermediate, intermediate_name, zokrates_code)
	cleanup = False
	if zokrates_path is None:
		tmp_dir = Path("/tmp/smt_solver")
		tmp_dir.mkdir(parents=True, exist_ok=True)
		zokrates_path = tmp_dir / intermediate_name
		zokrates_path.write_text(zokrates_code)
		cleanup = True

	_log(f"Compiling ZoKrates: {zokrates_path}", with_logs, log)
	try:
		r1cs_path = compile_zokrates_to_r1cs(zokrates_path, zokrates_path.parent, compiler=compiler or "zokrates")
		return parse_zokrates_r1cs(r1cs_path)
	finally:
		if cleanup:
			if zokrates_path.exists():
				zokrates_path.unlink()
			r1cs_path = zokrates_path.parent / f"{zokrates_path.stem}.r1cs"
			binary_path = zokrates_path.parent / zokrates_path.stem
			if r1cs_path.exists():
				r1cs_path.unlink()
			if binary_path.exists():
				binary_path.unlink()


def generate_ff_benchmarks(
	*,
	in_folder: Path,
	out_folder: Path,
	dsl: str,
	compiler: str | None,
	max_out: int | None,
	opt_level: str,
	suffix: str | None,
	max_vars: int | None,
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
			elif dsl == "zokrates":
				r1cs = _prepare_r1cs_from_zokrates(
					smtlib2,
					compiler=compiler,
					with_logs=with_logs,
					log=log,
					keep_intermediate=keep_intermediate,
				)
			else:
				raise ValueError(f"Unsupported DSL: {dsl}")

			if max_vars is not None and r1cs.nVars > max_vars:
				_log(
					f"Skipping {smt2_path.name}: nVars={r1cs.nVars} exceeds threshold {max_vars}",
					with_logs,
					log,
				)
				continue

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


def generate_ff_benchmark_suite(
	*,
	in_folder: Path,
	out_base: Path,
	max_vars: int,
	circom_compiler: str | None,
	gnark_compiler: str | None,
	zokrates_compiler: str | None,
	circom_opt_levels: tuple[str, ...],
	max_out: int | None,
	skip_existing: bool,
	continue_on_error: bool,
	with_logs: bool,
	keep_intermediate: Path | None,
	log=print,
):
	for opt_level in circom_opt_levels:
		generate_ff_benchmarks(
			in_folder=in_folder,
			out_folder=out_base,
			dsl="circom",
			compiler=circom_compiler,
			max_out=max_out,
			opt_level=opt_level,
			suffix=f"circom_{opt_level}",
			max_vars=max_vars,
			skip_existing=skip_existing,
			continue_on_error=continue_on_error,
			with_logs=with_logs,
			keep_intermediate=keep_intermediate,
			log=log,
		)

	generate_ff_benchmarks(
		in_folder=in_folder,
		out_folder=out_base,
		dsl="gnark",
		compiler=gnark_compiler,
		max_out=max_out,
		opt_level="O2",
		suffix="gnark",
		max_vars=max_vars,
		skip_existing=skip_existing,
		continue_on_error=continue_on_error,
		with_logs=with_logs,
		keep_intermediate=keep_intermediate,
		log=log,
	)

	generate_ff_benchmarks(
		in_folder=in_folder,
		out_folder=out_base,
		dsl="zokrates",
		compiler=zokrates_compiler,
		max_out=max_out,
		opt_level="O2",
		suffix="zokrates",
		max_vars=max_vars,
		skip_existing=skip_existing,
		continue_on_error=continue_on_error,
		with_logs=with_logs,
		keep_intermediate=keep_intermediate,
		log=log,
	)
