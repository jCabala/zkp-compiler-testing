from __future__ import annotations

import re
from typing import List


# -----------------------------
# SMT-LIB2 command splitting
# -----------------------------

def _strip_smtlib_comments(s: str) -> str:
    # SMT-LIB comments are from ';' to end-of-line (no block comments)
    return re.sub(r";.*?$", "", s, flags=re.M)


def _split_smtlib_commands(smt: str) -> List[str]:
    """
    Split an SMT-LIB2 script into top-level commands: each is one balanced (...) form.
    Robust to multi-line commands, ignores ';' line comments.

    Assumes no string literals containing parentheses (fine for your use case).
    """
    s = _strip_smtlib_comments(smt)

    cmds: List[str] = []
    i, n = 0, len(s)

    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break

        if s[i] != "(":
            i += 1
            continue

        start = i
        i += 1
        depth = 1

        while i < n and depth > 0:
            ch = s[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1

        if depth == 0:
            cmd = s[start:i].strip()
            if cmd:
                cmds.append(cmd)
        else:
            tail = s[start:].strip()
            if tail:
                cmds.append(tail)
            break

    return cmds


def _cmd_head_symbol(cmd: str) -> str:
    """
    Return the head symbol of a command, e.g. "(assert ...)" -> "assert".
    """
    j = 1
    while j < len(cmd) and cmd[j].isspace():
        j += 1
    k = j
    while k < len(cmd) and (not cmd[k].isspace()) and cmd[k] not in "()":
        k += 1
    return cmd[j:k]


def _reemit_script_with_single_assert(original_script: str, simplified_term_sexpr: str) -> str:
    """
    Keep all original top-level commands except asserts and query/execution commands,
    then append a single (assert <simplified>) and a final (check-sat).

    Does NOT add or modify (set-logic ...); it is copied from the original script.
    """
    cmds = _split_smtlib_commands(original_script)

    drop_heads = {
        "assert",
        "check-sat",
        "check-sat-assuming",
        "get-model",
        "get-value",
        "get-proof",
        "get-unsat-core",
        "get-assignment",
        "get-info",
        "get-option",
        "exit",
        # If your scripts use push/pop, global simplification across scopes is ambiguous.
        "push",
        "pop",
    }

    kept: List[str] = []
    for c in cmds:
        if _cmd_head_symbol(c) in drop_heads:
            continue
        kept.append(c)

    kept.append(f"(assert {simplified_term_sexpr})")
    kept.append("(check-sat)")
    return "\n".join(kept) + "\n"


def _reemit_script_with_assert_list(original_script: str, simplified_asserts: List[str]) -> str:
    """
    Keep original top-level non-assert commands, then append simplified asserts
    individually and finish with (check-sat).
    """
    cmds = _split_smtlib_commands(original_script)

    drop_heads = {
        "assert",
        "check-sat",
        "check-sat-assuming",
        "get-model",
        "get-value",
        "get-proof",
        "get-unsat-core",
        "get-assignment",
        "get-info",
        "get-option",
        "exit",
        "push",
        "pop",
    }

    kept: List[str] = []
    for c in cmds:
        if _cmd_head_symbol(c) in drop_heads:
            continue
        kept.append(c)

    if not simplified_asserts:
        kept.append("(assert true)")
    else:
        kept.extend(f"(assert {term})" for term in simplified_asserts)
    kept.append("(check-sat)")
    return "\n".join(kept) + "\n"


# -----------------------------
# Public API (Z3 only)
# -----------------------------

def simplify_formula(smtlib2_str: str) -> str:
    """
    Simplify an SMT-LIB2 script using Z3 and return a *new SMT-LIB2 script* that:
      - preserves original declarations/definitions/options (top-level)
      - replaces all asserts with one simplified assert of their conjunction
      - appends (check-sat)

    The original script is expected to already contain the declarations.
    """
    simplified = _simplify_term_z3(smtlib2_str)
    return _reemit_script_with_single_assert(smtlib2_str, simplified)


def simplify_formula_preserve_asserts(smtlib2_str: str) -> str:
    """
    Simplify each assert independently while preserving benchmark structure.

    Unlike simplify_formula(), this does not conjoin all assertions first, so
    UNSAT benchmarks do not collapse to a single `(assert false)` merely due to
    contradictions across different assertions.
    """
    simplified_asserts = _simplify_asserts_individually_z3(smtlib2_str)
    return _reemit_script_with_assert_list(smtlib2_str, simplified_asserts)


# -----------------------------
# Z3: parse -> simplify -> sexpr
# -----------------------------

_Z3_STRIP_EXEC_ONLY = re.compile(
    r"(?m)^\s*\((check-sat|check-sat-assuming|get-model|get-value|get-proof|get-unsat-core|get-assignment|get-info|get-option|exit)\b.*\)\s*$"
)

def _simplify_term_z3(smtlib2_str: str) -> str:
    try:
        import z3  # type: ignore
    except Exception as e:
        raise RuntimeError("Z3 Python bindings not available (pip install z3-solver).") from e

    # Keep decls/defs/asserts; remove query commands to avoid parse surprises.
    cleaned = _Z3_STRIP_EXEC_ONLY.sub("", smtlib2_str)

    assertions = z3.parse_smt2_string(cleaned)
    if not assertions:
        return z3.BoolVal(True).sexpr()

    phi = z3.And(*assertions)

    # Cheap but effective.
    phi = z3.simplify(phi)

    # Slightly stronger, still fast.
    g = z3.Goal()
    g.add(phi)
    t = z3.Then(z3.Tactic("simplify"), z3.Tactic("propagate-values"))
    res = t(g)

    if len(res) == 0 or len(res[0]) == 0:
        return z3.BoolVal(True).sexpr()

    return res[0].as_expr().sexpr()


def _simplify_asserts_individually_z3(smtlib2_str: str) -> List[str]:
    try:
        import z3  # type: ignore
        from z3 import z3util  # type: ignore
    except Exception as e:
        raise RuntimeError("Z3 Python bindings not available (pip install z3-solver).") from e

    cleaned = _Z3_STRIP_EXEC_ONLY.sub("", smtlib2_str)
    assertions = z3.parse_smt2_string(cleaned)
    if not assertions:
        return []

    tactic = z3.Then(z3.Tactic("simplify"), z3.Tactic("propagate-values"))
    simplified_terms: List[str] = []

    for assertion in assertions:
        original_has_vars = bool(z3util.get_vars(assertion))
        term = z3.simplify(assertion)
        g = z3.Goal()
        g.add(term)
        res = tactic(g)
        if len(res) == 0 or len(res[0]) == 0:
            term = z3.BoolVal(True)
        else:
            term = res[0].as_expr()

        if z3.is_true(term):
            continue
        if z3.is_false(term) and original_has_vars:
            simplified_terms.append(assertion.sexpr())
            continue
        if z3.is_false(term):
            continue
        simplified_terms.append(term.sexpr())

    return simplified_terms
