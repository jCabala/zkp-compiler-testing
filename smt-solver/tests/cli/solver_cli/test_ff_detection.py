from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.cli.solver_cli.commands import _is_qf_ff_formula
from src.smt_lib.smt_lib_parser import parse_smtlib2, parse_smtlib2_ff


def test_ff_detection_without_set_logic():
	smt2 = """(define-sort F () (_ FiniteField 17))
(declare-fun x () F)
(assert (= (ff.mul x x) x))
(check-sat)
"""
	assert _is_qf_ff_formula(smt2) is True


def test_ff_detection_with_ff_ops_only():
	smt2 = """(declare-fun x () F)
(assert (= (ff.add x (ff.neg x)) (as ff0 F)))
"""
	assert _is_qf_ff_formula(smt2) is True


def test_parse_qf_ff_boolean_connectives():
	smt2 = """(define-sort F () (_ FiniteField 17))
(declare-fun x () F)
(assert (and (= (ff.mul x x) x) (not (= x (as ff0 F)))))
(check-sat)
"""
	circuit = parse_smtlib2_ff(smt2)
	assert len(circuit.statements) == 1


def test_parse_smtlib2_auto_detects_ff_without_set_logic():
	smt2 = """(define-sort F () (_ FiniteField 17))
(declare-fun x () F)
(assert (and (= (ff.mul x x) x) (not (= x (as ff0 F)))))
(check-sat)
"""
	circuit = parse_smtlib2(smt2)
	assert len(circuit.statements) == 1
