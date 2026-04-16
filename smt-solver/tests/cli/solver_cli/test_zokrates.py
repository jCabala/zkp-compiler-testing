import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli import cli
from src.backends.circ.r1cs import parse_circ_r1cs_json
from src.cli.helper_tools_cli.translate_dsl import translate_smtlib2_to_dsl


DATA_DIR = Path(__file__).parent / "data"
SAT_FILE = DATA_DIR / "sat" / "sat_3vars.smt2"
UNSAT_FILE = DATA_DIR / "unsat" / "unsat_3vars.smt2"
FF_SAT_FILE = DATA_DIR / "ff" / "ff_sat_1.smt2"
FF_UNSAT_FILE = DATA_DIR / "ff" / "ff_unsat_1.smt2"
FF_PICUS_SAT_FILE = DATA_DIR / "ff" / "ff_picus_sat_1.smt2"
FF_PICUS_UNSAT_FILE = DATA_DIR / "ff" / "ff_picus_unsat_1.smt2"
PICUS_SAT_FILE = DATA_DIR / "picus_sat" / "picus_sat_1.smt2"
PICUS_UNSAT_FILE = DATA_DIR / "picus_unsat" / "picus_unsat_1.smt2"
TINY_UNSAT = """(set-logic QF_BV)
(declare-fun x () Bool)
(assert x)
(assert (not x))
(check-sat)
"""
TINY_FF_UNSAT = """(set-logic QF_FF)
(define-sort F () (_ FiniteField 101))
(assert (= (as ff1 F) (as ff2 F)))
(check-sat)
"""

pytestmark = pytest.mark.skipif(
	shutil.which("zokrates") is None,
	reason="ZoKrates is not installed",
)
PICUS_AVAILABLE = Path("~/Picus/run-picus").expanduser().exists()
CARGO_AVAILABLE = shutil.which("cargo") is not None


def _compile_zokrates_source(source: str, tmp_path: Path):
	source_path = tmp_path / "case.zok"
	out_path = tmp_path / "out"
	source_path.write_text(source)
	result = subprocess.run(
		["zokrates", "compile", "-i", str(source_path), "-o", str(out_path), "--curve", "bn128"],
		capture_output=True,
		text=True,
		check=False,
	)
	assert result.returncode == 0, result.stderr or result.stdout


def _assert_solve(smt_path: Path, solver: str, expected: str, *, with_hints: bool, with_circ: bool = False):
	args = [
		"solve",
		str(smt_path),
		"--zk-dsl",
		"zokrates",
		"--solver",
		solver,
		"--solving-timeout",
		"10",
	]
	if with_circ:
		args.append("--with-circ")
	if not with_hints:
		args.append("--without-hints")

	result = CliRunner().invoke(cli, args)
	assert result.exit_code == 0, f"Command failed:\n{result.output}"
	last_line = result.output.strip().splitlines()[-1]
	assert last_line == expected, f"Expected '{expected}', got:\n{result.output}"


def test_translate_bool_to_zokrates_compiles(tmp_path: Path):
	source, extension = translate_smtlib2_to_dsl(SAT_FILE.read_text(), "zokrates")
	assert extension == ".zok"
	assert "def main(" in source
	assert "private bool x1" in source
	assert "assert(" in source
	_compile_zokrates_source(source, tmp_path)


def test_translate_ff_to_zokrates_compiles(tmp_path: Path):
	source, extension = translate_smtlib2_to_dsl(FF_SAT_FILE.read_text(), "zokrates")
	assert extension == ".zok"
	assert "private field x" in source
	assert "return;" in source or "return " in source
	_compile_zokrates_source(source, tmp_path)


@pytest.mark.parametrize(
	("smt_path", "expected", "with_hints"),
	[
		(SAT_FILE, "sat", False),
		(SAT_FILE, "sat", True),
	],
)
def test_zokrates_solves_bool_formulas(smt_path: Path, expected: str, with_hints: bool):
	_assert_solve(smt_path, "z3", expected, with_hints=with_hints)


def test_zokrates_solves_tiny_unsat_formula(tmp_path: Path):
	smt_path = tmp_path / "tiny_unsat.smt2"
	smt_path.write_text(TINY_UNSAT)
	_assert_solve(smt_path, "z3", "unsat", with_hints=False)


def test_zokrates_solves_ff_sat_formula():
	_assert_solve(FF_SAT_FILE, "cvc5", "sat", with_hints=False)


def test_zokrates_solves_ff_unsat_formula():
	_assert_solve(FF_UNSAT_FILE, "cvc5", "unsat", with_hints=False)


def test_zokrates_dump_r1cs(tmp_path: Path):
	dump_path = tmp_path / "final.r1cs.txt"
	result = CliRunner().invoke(
		cli,
		[
			"solve",
			str(SAT_FILE),
			"--zk-dsl",
			"zokrates",
			"--solver",
			"z3",
			"--without-hints",
			"--dump-r1cs",
			str(dump_path),
		],
	)
	assert result.exit_code == 0, result.output
	assert dump_path.exists()
	dump_text = dump_path.read_text()
	assert "prime:" in dump_text
	assert "nConstraints:" in dump_text
	assert "bool_wires:" in dump_text


@pytest.mark.skipif(not PICUS_AVAILABLE, reason="Picus is not installed")
def test_zokrates_picus_roundtrip():
	_assert_solve(PICUS_SAT_FILE, "picus", "sat", with_hints=False)
	_assert_solve(PICUS_UNSAT_FILE, "picus", "unsat", with_hints=False)
	_assert_solve(FF_PICUS_SAT_FILE, "picus", "sat", with_hints=False)
	_assert_solve(FF_PICUS_UNSAT_FILE, "picus", "unsat", with_hints=False)


@pytest.mark.skipif(not CARGO_AVAILABLE, reason="Cargo is not installed")
def test_zokrates_with_circ_solves_sat_formula():
	_assert_solve(SAT_FILE, "z3", "sat", with_hints=False, with_circ=True)


@pytest.mark.skipif(not CARGO_AVAILABLE, reason="Cargo is not installed")
def test_zokrates_with_circ_solves_unsat_formula():
	_assert_solve(UNSAT_FILE, "z3", "unsat", with_hints=False, with_circ=True)


@pytest.mark.skipif(not CARGO_AVAILABLE, reason="Cargo is not installed")
def test_zokrates_with_circ_solves_ff_sat_formula():
	_assert_solve(FF_SAT_FILE, "cvc5", "sat", with_hints=False, with_circ=True)


@pytest.mark.skipif(not CARGO_AVAILABLE, reason="Cargo is not installed")
def test_zokrates_with_circ_solves_ff_unsat_formula():
	_assert_solve(FF_UNSAT_FILE, "cvc5", "unsat", with_hints=False, with_circ=True)


@pytest.mark.skipif(not (CARGO_AVAILABLE and PICUS_AVAILABLE), reason="Cargo or Picus is not installed")
def test_zokrates_with_circ_picus_roundtrip():
	_assert_solve(PICUS_SAT_FILE, "picus", "sat", with_hints=False, with_circ=True)
	_assert_solve(PICUS_UNSAT_FILE, "picus", "unsat", with_hints=False, with_circ=True)
	_assert_solve(FF_PICUS_SAT_FILE, "picus", "sat", with_hints=False, with_circ=True)
	_assert_solve(FF_PICUS_UNSAT_FILE, "picus", "unsat", with_hints=False, with_circ=True)


def test_parse_circ_r1cs_json(tmp_path: Path):
	json_path = tmp_path / "circ.json"
	json_path.write_text(
		"""
{
  "r1cs": {
    "field": {"IntField": ["101"]},
    "vars": [1, 2],
    "names": {"1": "x1", "2": "y"},
    "constraints": [
      [
        {"constant": 0, "monomials": {"1": 1}},
        {"constant": 0, "monomials": {}},
        {"constant": 0, "monomials": {"2": 1}}
      ]
    ],
    "commitments": []
  },
  "input_names": ["x1", "y"],
  "public_input_names": ["y"]
}
""".strip()
	)

	r1cs, name_to_wire, input_names, public_input_names = parse_circ_r1cs_json(json_path)

	assert r1cs.prime == 101
	assert r1cs.nVars == 3
	assert r1cs.nConstraints == 1
	assert name_to_wire == {"x1": 1, "y": 2}
	assert input_names == ["x1", "y"]
	assert public_input_names == {"y"}
	assert r1cs.constraints[0].A.terms[0].variable.index == 1
	assert r1cs.constraints[0].C.terms[0].variable.index == 2


def test_with_circ_requires_zokrates():
	result = CliRunner().invoke(
		cli,
		[
			"solve",
			str(SAT_FILE),
			"--zk-dsl",
			"circom",
			"--solver",
			"z3",
			"--with-circ",
			"--without-hints",
		],
	)
	assert result.exit_code != 0
	assert "--with-circ is only supported with --zk-dsl zokrates" in result.output
