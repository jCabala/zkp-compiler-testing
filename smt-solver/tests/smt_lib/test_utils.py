"""Unit tests for SMT-LIB v2 utility functions."""

import pytest
from src.smt_lib.utils import cnf_string_to_smt2


# ---- Helpers ----

def _check_sat(smt2: str) -> str:
    import z3
    assertions = z3.parse_smt2_string(smt2)
    s = z3.Solver()
    s.add(*assertions)
    return str(s.check())


# ---- Tests: output structure ----

class TestOutputStructure:
    def test_has_set_logic(self):
        cnf = "p cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(set-logic QF_BV)" in result

    def test_has_check_sat(self):
        cnf = "p cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(check-sat)" in result

    def test_has_get_model(self):
        cnf = "p cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(get-model)" in result

    def test_declares_all_variables(self):
        cnf = "p cnf 3 1\n1 2 3 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(declare-fun x1 () Bool)" in result
        assert "(declare-fun x2 () Bool)" in result
        assert "(declare-fun x3 () Bool)" in result

    def test_custom_var_prefix(self):
        cnf = "p cnf 2 1\n1 2 0\n"
        result = cnf_string_to_smt2(cnf, var_prefix="v")
        assert "(declare-fun v1 () Bool)" in result
        assert "(declare-fun v2 () Bool)" in result


# ---- Tests: clause translation ----

class TestClauseTranslation:
    def test_positive_literal(self):
        cnf = "p cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert x1)" in result

    def test_negative_literal(self):
        cnf = "p cnf 1 1\n-1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert (not x1))" in result

    def test_unit_clause(self):
        cnf = "p cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert x1)" in result

    def test_binary_clause(self):
        cnf = "p cnf 2 1\n1 2 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert (or x1 x2))" in result

    def test_ternary_clause(self):
        cnf = "p cnf 3 1\n1 2 3 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert (or x1 x2 x3))" in result

    def test_mixed_signs(self):
        cnf = "p cnf 2 1\n1 -2 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert (or x1 (not x2)))" in result

    def test_empty_clause_is_false(self):
        # A clause with only "0" is empty => false
        cnf = "p cnf 1 1\n0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert false)" in result

    def test_multiple_clauses(self):
        cnf = "p cnf 2 2\n1 0\n-2 0\n"
        result = cnf_string_to_smt2(cnf)
        assert result.count("(assert ") == 2


# ---- Tests: DIMACS parsing ----

class TestDimacsParsing:
    def test_comment_lines_ignored(self):
        cnf = "c this is a comment\np cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "comment" not in result
        assert "(assert x1)" in result

    def test_no_header(self):
        # Without header, nvars inferred from max variable
        cnf = "1 2 3 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(declare-fun x1 () Bool)" in result
        assert "(declare-fun x3 () Bool)" in result

    def test_header_nvars_respected(self):
        # Header says 5 vars but clause only uses 3 — should declare 5
        cnf = "p cnf 5 1\n1 2 3 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(declare-fun x4 () Bool)" in result
        assert "(declare-fun x5 () Bool)" in result

    def test_multiline_clause(self):
        # Clause split across lines
        cnf = "p cnf 3 1\n1 2\n3 0\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert (or x1 x2 x3))" in result

    def test_missing_trailing_zero(self):
        # Last clause without terminating 0 should still be included
        cnf = "p cnf 2 1\n1 2\n"
        result = cnf_string_to_smt2(cnf)
        assert "(assert (or x1 x2))" in result


# ---- Tests: satisfiability preservation ----

class TestSatisfiability:
    def test_sat_formula(self):
        # x1=T satisfies this
        cnf = "p cnf 1 1\n1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert _check_sat(result) == "sat"

    def test_unsat_formula(self):
        # x1 AND (NOT x1)
        cnf = "p cnf 1 2\n1 0\n-1 0\n"
        result = cnf_string_to_smt2(cnf)
        assert _check_sat(result) == "unsat"

    def test_multivar_sat(self):
        cnf = "p cnf 3 2\n1 2 0\n-1 3 0\n"
        result = cnf_string_to_smt2(cnf)
        assert _check_sat(result) == "sat"
