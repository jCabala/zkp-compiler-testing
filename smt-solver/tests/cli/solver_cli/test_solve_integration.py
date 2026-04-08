"""
Integration tests for the solve command.

Tests all combinations of:
- DSL backend: circom, gnark
- SMT solver: z3, cvc5, picus
- Oracle hints: off, on
Against SAT and UNSAT boolean formulas.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner
from cli import cli

DATA_DIR = Path(__file__).parent / "data"
SAT_FILES = sorted((DATA_DIR / "sat").glob("*.smt2"))
UNSAT_FILES = sorted((DATA_DIR / "unsat").glob("*.smt2"))
PICUS_SAT_FILES = sorted((DATA_DIR / "picus_sat").glob("*.smt2"))
PICUS_UNSAT_FILES = sorted((DATA_DIR / "picus_unsat").glob("*.smt2"))

DSLS = ["circom", "gnark"]
SMT_SOLVERS = ["z3", "cvc5"]
HINTS = [False, True]


def _assert_solve(smt_path, dsl, solver, with_hints, expected):
    args = [
        "solve",
        str(smt_path),
        "--zk-dsl", dsl,
        "--solver", solver,
    ]
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
