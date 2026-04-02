"""
Unit tests for progressive hints (--hint-models N).

Two test groups:
1. run_smt_solver_models — verifies model enumeration with blocking clauses
2. solve command aggregation — verifies sat/unsat aggregation over multiple oracle runs
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner
from cli import cli
from src.smt_lib.prune import run_smt_solver_models

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Formula with exactly 2 satisfying assignments: (x=T,y=F) and (x=F,y=T)
# xor forces both variables to be fully assigned in every model
FORMULA_2_MODELS = """\
(set-logic QF_BV)
(declare-fun x () Bool)
(declare-fun y () Bool)
(assert (xor x y))
(check-sat)
(get-model)
"""

# Formula with exactly 1 satisfying assignment: x=T, y=F
FORMULA_1_MODEL = """\
(set-logic QF_BV)
(declare-fun x () Bool)
(declare-fun y () Bool)
(assert x)
(assert (not y))
(check-sat)
(get-model)
"""

DATA_DIR = Path(__file__).parent / "data"
SAT_FILE = next((DATA_DIR / "sat").glob("*.smt2"))


# ---------------------------------------------------------------------------
# 1. run_smt_solver_models
# ---------------------------------------------------------------------------

class TestRunSMTSolverModels:
    def test_returns_up_to_max_models(self):
        _, models = run_smt_solver_models(FORMULA_2_MODELS, max_models=1)
        assert len(models) == 1

    def test_returns_all_models_when_fewer_than_max(self):
        # xor(x,y) has exactly 2 satisfying assignments; requesting 10 should return 2
        _, models = run_smt_solver_models(FORMULA_2_MODELS, max_models=10)
        assert len(models) == 2

    def test_models_are_distinct(self):
        _, models = run_smt_solver_models(FORMULA_2_MODELS, max_models=10)
        as_tuples = [tuple(sorted(m.items())) for m in models]
        assert len(set(as_tuples)) == len(as_tuples)

    def test_single_model_formula(self):
        _, models = run_smt_solver_models(FORMULA_1_MODEL, max_models=5)
        assert len(models) == 1
        assert models[0]["x"] is True
        assert models[0]["y"] is False

    def test_result_is_sat_when_models_found(self):
        result, models = run_smt_solver_models(FORMULA_2_MODELS, max_models=1)
        assert result == "sat"
        assert len(models) == 1


# ---------------------------------------------------------------------------
# 2. Aggregation in solve command
# ---------------------------------------------------------------------------

class TestProgressiveHintsAggregation:
    """
    Patches solve_circom so we control what each oracle run returns,
    then checks the final output of the solve command.
    """

    def _run(self, oracle_results: list[str]) -> str:
        """
        Invoke `solve` on a sat file, patching:
          - run_smt_solver_models → returns N fake models (one per oracle result)
          - solve_circom          → returns oracle_results in order
        Returns the last line of stdout.
        """
        fake_models = [{"x1": True}] * len(oracle_results)
        call_iter = iter(oracle_results)

        with patch("src.cli.solver_cli.commands.run_smt_solver_models", return_value=("sat", fake_models)), \
             patch("src.cli.solver_cli.commands.solve_circom", side_effect=lambda **_kw: next(call_iter)):
            result = CliRunner().invoke(cli, [
                "solve", str(SAT_FILE),
                "--zk-dsl", "circom",
                "--solver", "z3",
                f"--hint-models", str(len(oracle_results)),
            ])

        assert result.exit_code == 0, f"Command failed:\n{result.output}"
        return result.output.strip().splitlines()[-1]

    def test_all_sat_returns_sat(self):
        assert self._run(["sat", "sat", "sat"]) == "sat"

    def test_any_unsat_returns_unsat(self):
        assert self._run(["sat", "unsat", "sat"]) == "unsat"

    def test_all_unsat_returns_unsat(self):
        assert self._run(["unsat", "unsat"]) == "unsat"

    def test_single_model_sat(self):
        assert self._run(["sat"]) == "sat"

    def test_single_model_unsat(self):
        assert self._run(["unsat"]) == "unsat"

    def test_fewer_models_than_requested(self):
        """If formula only has 1 model, we run oracle once and still aggregate correctly."""
        fake_models = [{"x1": True}]  # only 1 even though hint_models=5
        with patch("src.cli.solver_cli.commands.run_smt_solver_models", return_value=("sat", fake_models)), \
             patch("src.cli.solver_cli.commands.solve_circom", return_value="sat"):
            result = CliRunner().invoke(cli, [
                "solve", str(SAT_FILE),
                "--zk-dsl", "circom",
                "--solver", "z3",
                "--hint-models", "5",
            ])
        assert result.exit_code == 0
        assert result.output.strip().splitlines()[-1] == "sat"
