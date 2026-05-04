from pathlib import Path
import sys
from unittest.mock import patch

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cli import cli
from src.r1cs.ir import Constraint, LinearCombination, R1CS, Term, Variable
from src.r1cs.solve import SMTResult


DATA_DIR = Path(__file__).parent / "data"
SAT_FILE = DATA_DIR / "sat" / "sat_3vars.smt2"


def _tiny_r1cs() -> R1CS:
    return R1CS(
        n8=0,
        prime=101,
        nVars=2,
        nOutputs=1,
        nPubInputs=0,
        nPrvInputs=1,
        nLabels=2,
        nConstraints=1,
        useCustomGates=False,
        variables=[Variable(0), Variable(1)],
        constraints=[
            Constraint(
                A=LinearCombination([Term(Variable(1), 1)]),
                B=LinearCombination([Term(Variable(0), 1)]),
                C=LinearCombination([]),
            )
        ],
    )


def test_solve_command_routes_to_noir_and_skips_hint_enumeration(tmp_path: Path):
    dump_path = tmp_path / "out.r1cs.txt"

    with patch("src.cli.solver_cli.commands.run_smt_solver_models") as run_models, \
         patch("src.cli.solver_cli.commands.run_ff_hint_models_subprocess") as run_ff_models, \
         patch("src.cli.solver_cli.commands.solve_noir", return_value="sat") as solve_noir:
        result = CliRunner().invoke(
            cli,
            [
                "solve",
                str(SAT_FILE),
                "--zk-dsl",
                "noir",
                "--solver",
                "z3",
                "--dump-r1cs",
                str(dump_path),
            ],
        )

    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == "sat"
    run_models.assert_not_called()
    run_ff_models.assert_not_called()
    solve_noir.assert_called_once()


def test_solve_noir_dump_r1cs(tmp_path: Path):
    from src.cli.solver_cli.noir import solve_noir

    dump_path = tmp_path / "noir_dump.txt"
    with patch("src.cli.solver_cli.noir.build_r1cs_from_noir", return_value=(_tiny_r1cs(), "(prime-number 101)\n")), \
         patch(
             "src.cli.solver_cli.noir.solve_r1cs",
             return_value=SMTResult(satisfiable=True, model={}),
         ) as solve_r1cs_mock:
        result = solve_noir(
            noir_path=tmp_path / "case.nr",
            with_model=False,
            with_logs=False,
            solver="z3",
            tmp_dir=tmp_path,
            dump_r1cs=dump_path,
        )

    assert result == "sat"
    assert dump_path.exists()
    assert "prime:" in dump_path.read_text()
    solve_r1cs_mock.assert_called_once()
