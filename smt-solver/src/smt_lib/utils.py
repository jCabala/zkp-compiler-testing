from __future__ import annotations

import re
from typing import List, Tuple, Optional


def cnf_string_to_smt2(cnf_text: str, *, var_prefix: str = "x") -> str:
    """
    Convert a DIMACS CNF provided as a string into SMT-LIB2 (QF_BV).

    - Supports standard DIMACS:
        * comment lines starting with 'c'
        * header line: 'p cnf <num_vars> <num_clauses>' (optional)
        * clauses: integers ending with 0, may span lines

    Returns:
        SMT-LIB2 string.
    """

    # 1) Strip comments, keep meaningful tokens
    tokens: List[str] = []
    declared_nvars: Optional[int] = None

    for raw_line in cnf_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("c"):
            continue

        # Header
        if line.startswith("p"):
            parts = line.split()
            if len(parts) >= 4 and parts[1] == "cnf":
                try:
                    declared_nvars = int(parts[2])
                    # declared_nclauses = int(parts[3])  # not strictly needed
                except ValueError:
                    pass
            continue

        # Clause/content line: collect tokens
        tokens.extend(line.split())

    # 2) Parse integers into clauses (each clause ends with 0)
    clauses: List[List[int]] = []
    current: List[int] = []

    def flush_current():
        nonlocal current
        # DIMACS allows empty clause: just "0"
        clauses.append(current)
        current = []

    for tok in tokens:
        # Some CNFs may include weird spacing; be defensive
        if not re.fullmatch(r"-?\d+", tok):
            continue

        lit = int(tok)
        if lit == 0:
            flush_current()
        else:
            current.append(lit)

    # If input forgot trailing 0, still keep what we saw
    if current:
        clauses.append(current)

    # 3) Determine number of variables
    max_var = 0
    for cl in clauses:
        for lit in cl:
            max_var = max(max_var, abs(lit))
    nvars = declared_nvars if declared_nvars is not None else max_var
    nvars = max(nvars, max_var)

    # 4) Helpers to emit SMT
    def v(i: int) -> str:
        return f"{var_prefix}{i}"

    def lit_to_smt(lit: int) -> str:
        if lit > 0:
            return v(lit)
        return f"(not {v(-lit)})"

    def clause_to_smt(clause: List[int]) -> str:
        if len(clause) == 0:
            # Empty clause => unsat
            return "false"
        if len(clause) == 1:
            return lit_to_smt(clause[0])
        return "(or " + " ".join(lit_to_smt(l) for l in clause) + ")"

    # 5) Build output
    out: List[str] = []
    out.append("(set-logic QF_BV)")
    for i in range(1, nvars + 1):
        out.append(f"(declare-fun {v(i)} () Bool)")

    for clause in clauses:
        out.append(f"(assert {clause_to_smt(clause)})")

    out.append("(check-sat)")
    out.append("(get-model)")
    return "\n".join(out)