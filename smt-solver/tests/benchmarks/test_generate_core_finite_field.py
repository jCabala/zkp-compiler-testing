from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "generate_core_finite_field.py"
SPEC = importlib.util.spec_from_file_location("generate_core_finite_field", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_assign_backends_uses_requested_split():
	core_files = [Path(f"case_{index:02d}.smt2") for index in range(8)]

	assignments = MODULE.assign_backends(core_files)
	labels = [backend.label for _, backend in assignments]

	assert labels.count("circom_O2") == 4
	assert labels.count("circom_O1") == 2
	assert labels.count("zokrates") == 2
	assert labels[:4] == ["circom_O2"] * 4
	assert labels[4:6] == ["circom_O1"] * 2
	assert labels[6:] == ["zokrates"] * 2


def test_main_mirrors_core_tree(monkeypatch, tmp_path: Path):
	core_dir = tmp_path / "core"
	out_dir = tmp_path / "finite-field"
	(core_dir / "sat").mkdir(parents=True)
	(core_dir / "unsat-simple").mkdir(parents=True)
	(core_dir / "sat" / "a.smt2").write_text("(check-sat)\n")
	(core_dir / "sat" / "b.smt2").write_text("(check-sat)\n")
	(core_dir / "unsat-simple" / "c.smt2").write_text("(check-sat)\n")
	(core_dir / "unsat-simple" / "d.smt2").write_text("(check-sat)\n")

	writes: list[tuple[Path, str]] = []

	def fake_convert_bool_smt_to_ff(**kwargs):
		out_file = kwargs["out_file"]
		out_file.parent.mkdir(parents=True, exist_ok=True)
		out_file.write_text(kwargs["dsl"])
		writes.append((out_file, kwargs["opt_level"]))
		return True

	monkeypatch.setattr(MODULE, "convert_bool_smt_to_ff", fake_convert_bool_smt_to_ff)
	monkeypatch.setattr(
		MODULE,
		"parse_args",
		lambda: MODULE.argparse.Namespace(
			core_dir=core_dir,
			out_dir=out_dir,
			circom_compiler=None,
			zokrates_compiler=None,
			max_vars=None,
			skip_existing=False,
			continue_on_error=False,
			with_logs=False,
			keep_intermediate=None,
		),
	)

	exit_code = MODULE.main()

	assert exit_code == 0
	assert sorted(path.relative_to(out_dir).as_posix() for path, _ in writes) == [
		"sat/a.smt2",
		"sat/b.smt2",
		"unsat-simple/c.smt2",
		"unsat-simple/d.smt2",
	]
	assert sorted((path.read_text(), opt_level) for path, opt_level in writes) == [
		("circom", "O1"),
		("circom", "O2"),
		("circom", "O2"),
		("zokrates", "O2"),
	]
