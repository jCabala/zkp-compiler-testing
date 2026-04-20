from pathlib import Path
import sys
from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from cli import cli
from src.r1cs.ir import Constraint
from tests.r1cs.conftest import make_r1cs, const


def _fake_r1cs():
	return make_r1cs(
		constraints=[Constraint(A=const(1), B=const(1), C=const(1))],
		nvars=1,
	)


def test_bool_smt_to_ff_circom(monkeypatch, tmp_path: Path):
	in_folder = tmp_path / "in"
	out_folder = tmp_path / "out"
	in_folder.mkdir()
	(in_folder / "case.smt2").write_text("(set-logic QF_BV)\n(assert true)\n(check-sat)\n")

	from src.cli.benchmark_gen_cli import bool_to_ff
	monkeypatch.setattr(bool_to_ff, "build_r1cs_from_circom", lambda *a, **k: _fake_r1cs())

	result = CliRunner().invoke(
		cli,
		[
			"bool-smt-to-ff",
			str(in_folder),
			str(out_folder),
			"--dsl",
			"circom",
		],
	)
	assert result.exit_code == 0, result.output
	out_file = out_folder / "case.smt2"
	assert out_file.exists()
	assert "QF_FF" in out_file.read_text()


def test_bool_smt_to_ff_gnark(monkeypatch, tmp_path: Path):
	in_folder = tmp_path / "in"
	out_folder = tmp_path / "out"
	in_folder.mkdir()
	(in_folder / "case.smt2").write_text("(set-logic QF_BV)\n(assert true)\n(check-sat)\n")

	from src.cli.benchmark_gen_cli import bool_to_ff
	monkeypatch.setattr(bool_to_ff, "build_r1cs_from_gnark", lambda *a, **k: (_fake_r1cs(), ""))

	result = CliRunner().invoke(
		cli,
		[
			"bool-smt-to-ff",
			str(in_folder),
			str(out_folder),
			"--dsl",
			"gnark",
			"--suffix",
			"gnark",
		],
	)
	assert result.exit_code == 0, result.output
	out_file = out_folder / "case--gnark.smt2"
	assert out_file.exists()
	assert "QF_FF" in out_file.read_text()


def test_bool_smt_to_ff_zokrates(monkeypatch, tmp_path: Path):
	in_folder = tmp_path / "in"
	out_folder = tmp_path / "out"
	in_folder.mkdir()
	(in_folder / "case.smt2").write_text("(set-logic QF_BV)\n(assert true)\n(check-sat)\n")

	from src.cli.benchmark_gen_cli import bool_to_ff
	monkeypatch.setattr(bool_to_ff, "compile_zokrates_to_r1cs", lambda *a, **k: tmp_path / "dummy.r1cs")
	monkeypatch.setattr(bool_to_ff, "parse_zokrates_r1cs", lambda *a, **k: _fake_r1cs())

	result = CliRunner().invoke(
		cli,
		[
			"bool-smt-to-ff",
			str(in_folder),
			str(out_folder),
			"--dsl",
			"zokrates",
		],
	)
	assert result.exit_code == 0, result.output
	out_file = out_folder / "case.smt2"
	assert out_file.exists()
	assert "QF_FF" in out_file.read_text()


def test_generate_ff_benchmark_suite(monkeypatch, tmp_path: Path):
	in_folder = tmp_path / "in"
	out_base = tmp_path / "out"
	in_folder.mkdir()
	(in_folder / "case.smt2").write_text("(set-logic QF_BV)\n(assert true)\n(check-sat)\n")

	from src.cli.benchmark_gen_cli import bool_to_ff
	monkeypatch.setattr(bool_to_ff, "build_r1cs_from_circom", lambda *a, **k: _fake_r1cs())
	monkeypatch.setattr(bool_to_ff, "build_r1cs_from_gnark", lambda *a, **k: (_fake_r1cs(), ""))
	monkeypatch.setattr(bool_to_ff, "compile_zokrates_to_r1cs", lambda *a, **k: tmp_path / "dummy.r1cs")
	monkeypatch.setattr(bool_to_ff, "parse_zokrates_r1cs", lambda *a, **k: _fake_r1cs())

	result = CliRunner().invoke(
		cli,
		[
			"generate-ff-benchmark-suite",
			str(in_folder),
			str(out_base),
			"--max-vars",
			"10",
		],
	)
	assert result.exit_code == 0, result.output
	assert (out_base / "case--circom_O0.smt2").exists()
	assert (out_base / "case--circom_O1.smt2").exists()
	assert (out_base / "case--circom_O2.smt2").exists()
	assert (out_base / "case--gnark.smt2").exists()
	assert (out_base / "case--zokrates.smt2").exists()
