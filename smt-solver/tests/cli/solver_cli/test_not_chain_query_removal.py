"""Regression tests for removing NOT-chain wires before SMT translation."""

from __future__ import annotations

import json
import random
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from cli import cli
from src.cli.solver_cli.not_chain import augment_smt2 as real_augment_smt2
from src.r1cs.ir import SMTResult

PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617

SIMPLE_BOOL_FORMULA = """\
(set-logic QF_BV)
(declare-fun x1 () Bool)
(assert x1)
(check-sat)
(get-model)
"""


def _write_formula(tmp_path: Path) -> Path:
    path = tmp_path / "input.smt2"
    path.write_text(SIMPLE_BOOL_FORMULA)
    return path


def _deterministic_augment(smt2: str, chain_length: int, max_count: int):
    return real_augment_smt2(smt2, chain_length, max_count, rng=random.Random(0))


def _constraint_wire_indices(r1cs) -> set[int]:
    indices: set[int] = set()
    for constraint in r1cs.constraints:
        for lc in (constraint.A, constraint.B, constraint.C):
            for term in lc.terms:
                indices.add(term.variable.index)
    return indices


def test_circom_not_chain_wires_do_not_reach_final_query(tmp_path):
    """
    The final Circom R1CS handed to the SMT solver should not mention
    _removable_ wires or helper wires derived only from them.
    """
    smt_path = _write_formula(tmp_path)
    captured: dict[str, object] = {}

    circom_json = json.dumps(
        {
            "n8": 32,
            "prime": str(PRIME),
            "nVars": 5,
            "nOutputs": 0,
            "nPubInputs": 0,
            "nPrvInputs": 2,
            "nLabels": 5,
            "nConstraints": 3,
            "useCustomGates": False,
            "constraints": [
                [
                    {"1": "1", "2": "1", "3": str(PRIME - 1)},
                    {"0": "1"},
                    {},
                ],
                [
                    {"3": "1", "4": str(PRIME - 1)},
                    {"0": "1"},
                    {},
                ],
                [
                    {"1": "1"},
                    {"0": "1"},
                    {"0": "1"},
                ]
            ],
            "map": [0, 1, 2, 30, 31],
            "customGates": [],
            "customGatesUses": [],
        }
    )

    def fake_get_r1cs_with_sym(_circom_path, opt_flag=None, bool_signal_names=None, compiler="circom"):
        assert "main._removable_1_1" in (bool_signal_names or [])
        return circom_json, {1, 2}, {2}, {1}

    def fake_solve_r1cs(r1cs, backend="z3", with_logs=False, solving_timeout=None):
        captured["r1cs"] = r1cs
        return SMTResult(True, {})

    with patch("src.cli.solver_cli.commands.augment_smt2", side_effect=_deterministic_augment), \
         patch("src.backends.circom.r1cs.get_r1cs_with_sym", side_effect=fake_get_r1cs_with_sym), \
         patch("src.cli.solver_cli.circom.optimize_r1cs", side_effect=lambda r1cs, with_logs=False: r1cs), \
         patch("src.cli.solver_cli.circom.solve_r1cs", side_effect=fake_solve_r1cs):
        result = CliRunner().invoke(
            cli,
            [
                "solve",
                str(smt_path),
                "--zk-dsl",
                "circom",
                "--solver",
                "z3",
                "--without-hints",
                "--no-simplify",
                "--not-chain-length",
                "1",
                "--max-not-chain-count",
                "1",
            ],
        )

    assert result.exit_code == 0, result.output
    final_r1cs = captured["r1cs"]
    assert [var.index for var in final_r1cs.variables] == [0, 1]
    assert _constraint_wire_indices(final_r1cs) == {0, 1}
    assert final_r1cs.nConstraints == 1


def test_gnark_not_chain_wires_do_not_reach_final_query(tmp_path):
    """The same transitive removal contract should hold for the Gnark backend."""
    smt_path = _write_formula(tmp_path)
    captured: dict[str, object] = {}

    sr1cs = f"""\
(prime-number {PRIME})
(in 1)
(label 1 x1)
(label 2 _removable_1_1)
(label 3 helper_a)
(label 4 helper_b)
(constraint [(c1 1) (c1 2) ({PRIME - 1} 3)] [(c1 0)] [])
(constraint [(c1 3) ({PRIME - 1} 4)] [(c1 0)] [])
(constraint [(c1 1)] [(c1 0)] [(c1 0)])
"""

    def fake_get_r1cs_sr1cs(_gnark_path, compiler="go"):
        return sr1cs

    def fake_solve_r1cs(r1cs, backend="z3", with_logs=False, solving_timeout=None):
        captured["r1cs"] = r1cs
        return SMTResult(True, {})

    with patch("src.cli.solver_cli.commands.augment_smt2", side_effect=_deterministic_augment), \
         patch("src.backends.gnark.r1cs.get_r1cs_sr1cs", side_effect=fake_get_r1cs_sr1cs), \
         patch("src.cli.solver_cli.gnark.maybe_clean_go_cache", return_value=None), \
         patch("src.cli.solver_cli.gnark.optimize_r1cs", side_effect=lambda r1cs, with_logs=False: r1cs), \
         patch("src.cli.solver_cli.gnark.solve_r1cs", side_effect=fake_solve_r1cs):
        result = CliRunner().invoke(
            cli,
            [
                "solve",
                str(smt_path),
                "--zk-dsl",
                "gnark",
                "--solver",
                "z3",
                "--without-hints",
                "--no-simplify",
                "--not-chain-length",
                "1",
                "--max-not-chain-count",
                "1",
            ],
        )

    assert result.exit_code == 0, result.output
    final_r1cs = captured["r1cs"]
    assert [var.index for var in final_r1cs.variables] == [0, 1]
    assert _constraint_wire_indices(final_r1cs) == {0, 1}
    assert final_r1cs.nConstraints == 1
