"""Unit tests for SMT-LIB v2 formula simplification."""

import pytest
from src.smt_lib.simplify import (
    simplify_formula,
    _strip_smtlib_comments,
    _split_smtlib_commands,
    _cmd_head_symbol,
)


# ---- Helpers ----

def _formula(body: str, vars: list[str] = None) -> str:
    if vars is None:
        vars = ["x", "y", "z"]
    decls = "\n".join(f"(declare-fun {v} () Bool)" for v in vars)
    return f"(set-logic QF_UF)\n{decls}\n{body}\n(check-sat)"

def _check_sat_with_z3(smt2: str) -> str:
    """Run z3 on an SMT-LIB formula and return 'sat' or 'unsat'."""
    import z3
    assertions = z3.parse_smt2_string(smt2)
    s = z3.Solver()
    s.add(*assertions)
    result = s.check()
    return str(result)


# ---- Tests: _strip_smtlib_comments ----

class TestStripComments:
    def test_removes_line_comment(self):
        assert _strip_smtlib_comments("; this is a comment\n(assert x)") == "\n(assert x)"

    def test_removes_inline_comment(self):
        assert _strip_smtlib_comments("(assert x) ; inline comment").strip() == "(assert x)"

    def test_no_comments(self):
        s = "(declare-fun x () Bool)"
        assert _strip_smtlib_comments(s) == s

    def test_multiple_comments(self):
        s = "; line 1\n; line 2\n(assert x)"
        result = _strip_smtlib_comments(s)
        assert "(assert x)" in result
        assert "line 1" not in result
        assert "line 2" not in result


# ---- Tests: _split_smtlib_commands ----

class TestSplitCommands:
    def test_single_command(self):
        cmds = _split_smtlib_commands("(check-sat)")
        assert cmds == ["(check-sat)"]

    def test_multiple_commands(self):
        cmds = _split_smtlib_commands("(declare-fun x () Bool)\n(assert x)\n(check-sat)")
        assert len(cmds) == 3

    def test_nested_parens(self):
        cmds = _split_smtlib_commands("(assert (and x (or y z)))")
        assert len(cmds) == 1
        assert "and" in cmds[0]

    def test_strips_comments_first(self):
        cmds = _split_smtlib_commands("; comment\n(assert x)")
        assert len(cmds) == 1
        assert cmds[0] == "(assert x)"

    def test_empty_input(self):
        assert _split_smtlib_commands("") == []

    def test_multiline_command(self):
        cmds = _split_smtlib_commands("(assert\n  (and x\n       y))")
        assert len(cmds) == 1


# ---- Tests: _cmd_head_symbol ----

class TestCmdHeadSymbol:
    def test_assert(self):
        assert _cmd_head_symbol("(assert x)") == "assert"

    def test_declare_fun(self):
        assert _cmd_head_symbol("(declare-fun x () Bool)") == "declare-fun"

    def test_check_sat(self):
        assert _cmd_head_symbol("(check-sat)") == "check-sat"

    def test_with_leading_space(self):
        assert _cmd_head_symbol("(  set-logic QF_BV)") == "set-logic"


# ---- Tests: simplify_formula ----

class TestSimplifyFormula:
    def test_preserves_declarations(self):
        smt2 = _formula("(assert x)", vars=["x"])
        result = simplify_formula(smt2)
        assert "(declare-fun x () Bool)" in result

    def test_preserves_set_logic(self):
        smt2 = _formula("(assert x)", vars=["x"])
        result = simplify_formula(smt2)
        assert "(set-logic" in result

    def test_output_has_check_sat(self):
        smt2 = _formula("(assert x)", vars=["x"])
        result = simplify_formula(smt2)
        assert "(check-sat)" in result

    def test_sat_preserving(self):
        smt2 = _formula("(assert x)\n(assert (not y))", vars=["x", "y"])
        result = simplify_formula(smt2)
        assert _check_sat_with_z3(result) == "sat"

    def test_unsat_preserving(self):
        smt2 = _formula("(assert x)\n(assert (not x))", vars=["x"])
        result = simplify_formula(smt2)
        assert _check_sat_with_z3(result) == "unsat"

    def test_simplifies_tautology(self):
        # (or x (not x)) should simplify to true
        smt2 = _formula("(assert (or x (not x)))", vars=["x"])
        result = simplify_formula(smt2)
        assert "true" in result.lower()

    def test_simplifies_contradiction(self):
        # (and x (not x)) should simplify to false
        smt2 = _formula("(assert (and x (not x)))", vars=["x"])
        result = simplify_formula(smt2)
        assert "false" in result.lower()

    def test_simplifies_constant_propagation(self):
        # (and true x) should simplify to just x
        smt2 = _formula("(assert (and true x))", vars=["x"])
        result = simplify_formula(smt2)
        simplified_assert = [l for l in result.splitlines() if "(assert " in l][0]
        assert "true" not in simplified_assert
