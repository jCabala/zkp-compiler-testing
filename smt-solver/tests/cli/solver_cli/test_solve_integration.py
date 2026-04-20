"""
Integration tests for the solve command.

Tests all combinations of:
- DSL backend: circom, gnark, zokrates
- SMT solver: z3, cvc5, picus
- Oracle hints: off, on
Against SAT and UNSAT boolean formulas.
"""

import shutil
import pytest
from pathlib import Path
from click.testing import CliRunner
from cli import cli

DATA_DIR = Path(__file__).parent / "data"
SAT_FILES = sorted((DATA_DIR / "sat").glob("*.smt2"))
UNSAT_FILES = sorted((DATA_DIR / "unsat").glob("*.smt2"))
PICUS_SAT_FILES = sorted((DATA_DIR / "picus_sat").glob("*.smt2"))
PICUS_UNSAT_FILES = sorted((DATA_DIR / "picus_unsat").glob("*.smt2"))
FF_SAT_FILES = sorted((DATA_DIR / "ff").glob("ff_sat_*.smt2"))
FF_UNSAT_FILES = sorted((DATA_DIR / "ff").glob("ff_unsat_*.smt2"))
FF_PICUS_SAT_FILES = sorted((DATA_DIR / "ff").glob("ff_picus_sat_*.smt2"))
FF_PICUS_UNSAT_FILES = sorted((DATA_DIR / "ff").glob("ff_picus_unsat_*.smt2"))
BASE_DSLS = ["circom", "gnark"]
ZOKRATES_AVAILABLE = shutil.which("zokrates") is not None
DSLS = BASE_DSLS + (["zokrates"] if ZOKRATES_AVAILABLE else [])
SMT_SOLVERS = ["z3", "cvc5"]
HINTS = [False, True]
CARGO_AVAILABLE = shutil.which("cargo") is not None
ZOKRATES_WITH_CIRC_AVAILABLE = ZOKRATES_AVAILABLE and CARGO_AVAILABLE


def _assert_solve(smt_path, dsl, solver, with_hints, expected, *, with_circ=False):
    args = [
        "solve",
        str(smt_path),
        "--zk-dsl", dsl,
        "--solver", solver,
    ]
    if with_circ:
        args.append("--with-circ")
    if not with_hints:
        args.append("--without-hints")
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, f"Command failed:\n{result.output}"
    last_line = result.output.strip().splitlines()[-1]
    assert last_line == expected, (
        f"Expected '{expected}', got:\n{result.output}"
    )


# ---------------------- z3 / cvc5 tests ----------------------

@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("solver", SMT_SOLVERS)
@pytest.mark.parametrize("with_hints", HINTS, ids=["no-hints", "with-hints"])
@pytest.mark.parametrize("smt_file", SAT_FILES, ids=[f.stem for f in SAT_FILES])
def test_sat_formulas(smt_file, dsl, solver, with_hints):
    """SAT formulas should produce 'sat' output."""
    _assert_solve(smt_file, dsl, solver, with_hints, "sat")


@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("solver", SMT_SOLVERS)
@pytest.mark.parametrize("with_hints", HINTS, ids=["no-hints", "with-hints"])
@pytest.mark.parametrize("smt_file", UNSAT_FILES, ids=[f.stem for f in UNSAT_FILES])
def test_unsat_formulas(smt_file, dsl, solver, with_hints):
    """UNSAT formulas should produce 'unsat' output."""
    _assert_solve(smt_file, dsl, solver, with_hints, "unsat")


# ---------------------- picus tests ----------------------

@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("with_hints", HINTS, ids=["no-hints", "with-hints"])
@pytest.mark.parametrize("smt_file", PICUS_SAT_FILES, ids=[f.stem for f in PICUS_SAT_FILES])
def test_picus_sat_formulas(smt_file, dsl, with_hints):
    """Properly constrained formulas should produce 'sat' output with picus."""
    _assert_solve(smt_file, dsl, "picus", with_hints, "sat")


@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("smt_file", PICUS_UNSAT_FILES, ids=[f.stem for f in PICUS_UNSAT_FILES])
def test_picus_unsat_formulas(smt_file, dsl):
    """Underconstrained formulas should produce 'unsat' output with picus.

    Always run without hints: hints pin free variables, which can make picus
    see an underconstrained circuit as properly constrained, producing a false
    'sat' result.
    """
    # with_hints=False is intentional and must not be changed — see docstring
    _assert_solve(smt_file, dsl, "picus", False, "unsat")


# ---------------------- QF_FF tests ----------------------

@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("solver", ["cvc5"])
@pytest.mark.parametrize("with_hints", HINTS, ids=["no-hints", "with-hints"])
@pytest.mark.parametrize("smt_file", FF_SAT_FILES, ids=[f.stem for f in FF_SAT_FILES])
def test_ff_sat_formulas(smt_file, dsl, solver, with_hints):
	_assert_solve(smt_file, dsl, solver, with_hints, "sat")


@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("solver", ["cvc5"])
@pytest.mark.parametrize("with_hints", HINTS, ids=["no-hints", "with-hints"])
@pytest.mark.parametrize("smt_file", FF_UNSAT_FILES, ids=[f.stem for f in FF_UNSAT_FILES])
def test_ff_unsat_formulas(smt_file, dsl, solver, with_hints):
	_assert_solve(smt_file, dsl, solver, with_hints, "unsat")


@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("with_hints", HINTS, ids=["no-hints", "with-hints"])
@pytest.mark.parametrize("smt_file", FF_PICUS_SAT_FILES, ids=[f.stem for f in FF_PICUS_SAT_FILES])
def test_ff_picus_sat_formulas(smt_file, dsl, with_hints):
	_assert_solve(smt_file, dsl, "picus", with_hints, "sat")


@pytest.mark.parametrize("dsl", DSLS)
@pytest.mark.parametrize("smt_file", FF_PICUS_UNSAT_FILES, ids=[f.stem for f in FF_PICUS_UNSAT_FILES])
def test_ff_picus_unsat_formulas(smt_file, dsl):
	_assert_solve(smt_file, dsl, "picus", False, "unsat")


# ---------------------- zokrates + circ tests ----------------------

@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("solver", ["z3"])
@pytest.mark.parametrize("with_hints", [False], ids=["no-hints"])
@pytest.mark.parametrize("smt_file", SAT_FILES, ids=[f.stem for f in SAT_FILES])
def test_zokrates_with_circ_sat_formulas(smt_file, solver, with_hints):
    _assert_solve(smt_file, "zokrates", solver, with_hints, "sat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("solver", ["z3"])
@pytest.mark.parametrize("with_hints", [False], ids=["no-hints"])
@pytest.mark.parametrize("smt_file", UNSAT_FILES, ids=[f.stem for f in UNSAT_FILES])
def test_zokrates_with_circ_unsat_formulas(smt_file, solver, with_hints):
    _assert_solve(smt_file, "zokrates", solver, with_hints, "unsat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("with_hints", [False], ids=["no-hints"])
@pytest.mark.parametrize("smt_file", PICUS_SAT_FILES, ids=[f.stem for f in PICUS_SAT_FILES])
def test_zokrates_with_circ_picus_sat_formulas(smt_file, with_hints):
    _assert_solve(smt_file, "zokrates", "picus", with_hints, "sat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("smt_file", PICUS_UNSAT_FILES, ids=[f.stem for f in PICUS_UNSAT_FILES])
def test_zokrates_with_circ_picus_unsat_formulas(smt_file):
    _assert_solve(smt_file, "zokrates", "picus", False, "unsat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("solver", ["cvc5"])
@pytest.mark.parametrize("with_hints", [False], ids=["no-hints"])
@pytest.mark.parametrize("smt_file", FF_SAT_FILES, ids=[f.stem for f in FF_SAT_FILES])
def test_zokrates_with_circ_ff_sat_formulas(smt_file, solver, with_hints):
    _assert_solve(smt_file, "zokrates", solver, with_hints, "sat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("solver", ["cvc5"])
@pytest.mark.parametrize("with_hints", [False], ids=["no-hints"])
@pytest.mark.parametrize("smt_file", FF_UNSAT_FILES, ids=[f.stem for f in FF_UNSAT_FILES])
def test_zokrates_with_circ_ff_unsat_formulas(smt_file, solver, with_hints):
    _assert_solve(smt_file, "zokrates", solver, with_hints, "unsat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("with_hints", [False], ids=["no-hints"])
@pytest.mark.parametrize("smt_file", FF_PICUS_SAT_FILES, ids=[f.stem for f in FF_PICUS_SAT_FILES])
def test_zokrates_with_circ_ff_picus_sat_formulas(smt_file, with_hints):
    _assert_solve(smt_file, "zokrates", "picus", with_hints, "sat", with_circ=True)


@pytest.mark.skipif(not ZOKRATES_WITH_CIRC_AVAILABLE, reason="ZoKrates or cargo is not installed")
@pytest.mark.parametrize("smt_file", FF_PICUS_UNSAT_FILES, ids=[f.stem for f in FF_PICUS_UNSAT_FILES])
def test_zokrates_with_circ_ff_picus_unsat_formulas(smt_file):
    _assert_solve(smt_file, "zokrates", "picus", False, "unsat", with_circ=True)
