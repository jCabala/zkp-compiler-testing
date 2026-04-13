from io import StringIO
from typing import Dict, List, Tuple
import re

from src.smt_lib.zk_ir import (
    Circuit,
    Assertion,
    Expression,
    FusedVariable,
    Variable,
    Integer,
    Boolean,
    UnaryExpression,
    BinaryExpression,
    Operator,
    VariableType,
)

FUSION_SUFFIX = "_fused"


# ------------------------------------------------------------
# XOR fusion inference from variable naming convention
# ------------------------------------------------------------

def _infer_xor_fusion(var_name: str) -> Expression:
    """
    Infer XOR fusion expression from a fused variable's name.

    Naming conventions:
      Original:      scr1_x1_scr1_x2_fused  (split on second "scr")
      After pruning:  var1__var2__orig__<original>_fused  (split on "__")
      Components may be literal "true"/"false" if pruning substituted them.
    """
    base = var_name[: -len(FUSION_SUFFIX)]

    if "__" in base:
        parts = base.split("__")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse renamed fused name: {var_name}")
        var1, var2 = parts[0], parts[1]
    else:
        first = base.find("scr")
        if first == -1:
            raise ValueError(f"Cannot parse fused name (no 'scr'): {var_name}")
        second = base.find("scr", first + 1)
        if second == -1:
            raise ValueError(f"Cannot parse fused name (no second 'scr'): {var_name}")
        var1 = base[:second].rstrip("_")
        var2 = base[second:]

    def _to_expr(name: str) -> Expression:
        if name == "true":
            return Boolean(True)
        if name == "false":
            return Boolean(False)
        return Variable(name, VariableType.BOOLEAN)

    return BinaryExpression(Operator.LXOR, _to_expr(var1), _to_expr(var2))


# ------------------------------------------------------------
# SUM fusion inference from variable naming convention (FF)
# ------------------------------------------------------------

def _infer_sum_fusion(var_name: str) -> Expression:
    """
    Infer SUM fusion expression from a fused variable's name.

    Naming conventions:
      Original:      scr1_x1_scr1_x2_fused  (split on second "scr")
      After pruning:  var1__var2__orig__<original>_fused  (split on "__")
    """
    base = var_name[: -len(FUSION_SUFFIX)]

    if "__" in base:
        parts = base.split("__")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse renamed fused name: {var_name}")
        var1, var2 = parts[0], parts[1]
    else:
        first = base.find("scr")
        if first == -1:
            raise ValueError(f"Cannot parse fused name (no 'scr'): {var_name}")
        second = base.find("scr", first + 1)
        if second == -1:
            raise ValueError(f"Cannot parse fused name (no second 'scr'): {var_name}")
        var1 = base[:second].rstrip("_")
        var2 = base[second:]

    return BinaryExpression(
        Operator.ADD,
        Variable(var1, VariableType.FIELD),
        Variable(var2, VariableType.FIELD),
    )


# ------------------------------------------------------------
# Main parser: SMT-LIB v2 (boolean-only) → Circuit IR
# ------------------------------------------------------------

def parse_smtlib2_core(smtlib2: str, solver: str = "z3") -> Circuit:
    """
    Parse a boolean-only SMT-LIB v2 formula into a Circuit IR.

    Supported operations: boolean core (and, or, not, =>, <=>, =)
    All variables are treated as VariableType.BOOLEAN.
    Fused variables (XOR) are detected by the '_fused' name suffix.
    """

    # The below "hack" should no longer be needed as we run cvc5 in a separate process, but lets keep it here as a reference just in case of future issues between cvc5 and pySMT.
    # if solver == "cvc5":
    #     # ------------------------------------------------------------------
    #     # THIS IMPORT NEEDS TO STAY TO AVOID PROBLEMS BETWEEN PYSMT AND CVC5
    #     import cvc5.pythonic
    #     # ------------------------------------------------------------------

    from pysmt.smtlib.parser import SmtLibParser
    from pysmt.fnode import FNode
    from pysmt.smtlib.script import SmtLibScript
    from pysmt import operators as op

    def parse_smtlib2_to_pysmt_ir(smtlib2: str) -> Tuple[SmtLibScript, List[FNode]]:
        parser = SmtLibParser()
        script = parser.get_script(StringIO(smtlib2))

        assertions: List[FNode] = []
        for cmd in script.commands:
            if cmd.name == "assert":
                assertions.append(cmd.args[0])

        return script, assertions

    script, assertions = parse_smtlib2_to_pysmt_ir(smtlib2)

    # Extract variables from declare-fun commands
    inputs: List[Variable] = []
    outputs: List[Variable] = []

    for cmd in script.commands:
        if cmd.name == "declare-fun":
            name = str(cmd.args[0])

            if name.endswith(FUSION_SUFFIX):
                outputs.append(
                    FusedVariable(name, VariableType.BOOLEAN, _infer_xor_fusion(name))
                )
            else:
                inputs.append(Variable(name, VariableType.BOOLEAN))

        elif cmd.name == "define-fun":
            raise NotImplementedError("define-fun is not supported in this parser")

    def fold_left(opcode: Operator, exprs: List[Expression]) -> Expression:
        out = exprs[0]
        for e in exprs[1:]:
            out = BinaryExpression(opcode, out, e)
        return out

    def fnode_to_zkir(node: FNode, env: Dict[str, Expression] | None = None) -> Expression:
        """Convert a pySMT AST node to a zk_ir Expression. env implements let-substitution."""
        if env is None:
            env = {}

        nt = node.node_type()

        match nt:
            case op.SYMBOL:
                name = node.symbol_name()
                if name in env:
                    return env[name]
                return Variable(name, VariableType.BOOLEAN)

            case op.BOOL_CONSTANT:
                return Boolean(bool(node.constant_value()))

            case op.NOT:
                return UnaryExpression(Operator.NOT, fnode_to_zkir(node.arg(0), env))

            case op.AND:
                args = [fnode_to_zkir(a, env) for a in node.args()]
                return fold_left(Operator.LAND, args)

            case op.OR:
                args = [fnode_to_zkir(a, env) for a in node.args()]
                return fold_left(Operator.LOR, args)

            case op.IMPLIES:
                return BinaryExpression(
                    Operator.LOR,
                    UnaryExpression(Operator.NOT, fnode_to_zkir(node.arg(0), env)),
                    fnode_to_zkir(node.arg(1), env),
                )

            case op.IFF:
                return BinaryExpression(
                    Operator.EQU,
                    fnode_to_zkir(node.arg(0), env),
                    fnode_to_zkir(node.arg(1), env),
                )

            case op.EQUALS:
                return BinaryExpression(
                    Operator.EQU,
                    fnode_to_zkir(node.arg(0), env),
                    fnode_to_zkir(node.arg(1), env),
                )

            case _:
                raise NotImplementedError(f"Unsupported node type: {nt} ({node})")

    statements: List[Assertion] = []
    for idx, fnode in enumerate(assertions):
        expr = fnode_to_zkir(fnode)
        statements.append(Assertion(identifier=f"assert_{idx}", value=expr))

    return Circuit(
        name="smtlib2_bool",
        inputs=inputs,
        outputs=outputs,
        statements=statements,
    )


# ------------------------------------------------------------
# Finite-field parser: SMT-LIB v2 (QF_FF subset) → Circuit IR
# ------------------------------------------------------------

def _strip_smt_comments(s: str) -> str:
    lines = []
    for line in s.splitlines():
        if ";" in line:
            line = line.split(";", 1)[0]
        if line.strip():
            lines.append(line)
    return "\n".join(lines)


def _tokenize_sexpr(s: str) -> list[str]:
    tokens: list[str] = []
    buf: list[str] = []
    for ch in s:
        if ch in ("(", ")"):
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        elif ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def _parse_sexpr(tokens: list[str], idx: int = 0):
    if idx >= len(tokens):
        raise ValueError("Unexpected end of tokens")
    tok = tokens[idx]
    if tok == "(":
        out = []
        idx += 1
        while idx < len(tokens) and tokens[idx] != ")":
            node, idx = _parse_sexpr(tokens, idx)
            out.append(node)
        if idx >= len(tokens) or tokens[idx] != ")":
            raise ValueError("Unbalanced parentheses in SMT-LIB")
        return out, idx + 1
    if tok == ")":
        raise ValueError("Unexpected ')'")
    return tok, idx + 1


def _parse_script(s: str) -> list:
    tokens = _tokenize_sexpr(s)
    idx = 0
    forms = []
    while idx < len(tokens):
        node, idx = _parse_sexpr(tokens, idx)
        forms.append(node)
    return forms


def parse_smtlib2_ff(smtlib2: str) -> Circuit:
    """
    Parse a finite-field SMT-LIB v2 formula (QF_FF subset) into a Circuit IR.

    Supported:
      - (set-logic QF_FF)
      - (define-sort F () (_ FiniteField p))
      - (declare-fun x () F)
      - (assert (= <expr> <expr>))
      - ff.add / ff.mul / ff.neg
      - constants (as ffK F)
    """
    cleaned = _strip_smt_comments(smtlib2)
    forms = _parse_script(cleaned)

    declared: set[str] = set()
    inputs: list[Variable] = []
    outputs: list[Variable] = []
    assertions: list[Assertion] = []

    def _to_int_atom(atom: str) -> int | None:
        if atom.isdigit() or (atom.startswith("-") and atom[1:].isdigit()):
            return int(atom)
        if atom.startswith("ff") and atom[2:].isdigit():
            return int(atom[2:])
        return None

    def _fold_left(opcode: Operator, exprs: list[Expression]) -> Expression:
        out = exprs[0]
        for e in exprs[1:]:
            out = BinaryExpression(opcode, out, e)
        return out

    def _expr(node) -> Expression:
        if isinstance(node, str):
            maybe_int = _to_int_atom(node)
            if maybe_int is not None:
                return Integer(maybe_int)
            if node in declared:
                return Variable(node, VariableType.FIELD)
            raise ValueError(f"Unknown symbol in QF_FF expression: {node}")

        if not node:
            raise ValueError("Empty expression in QF_FF")

        head = node[0]
        if head == "as":
            if len(node) != 3:
                raise ValueError(f"Malformed (as ...) constant: {node}")
            ff_token = node[1]
            maybe_int = _to_int_atom(ff_token)
            if maybe_int is None:
                raise ValueError(f"Unsupported constant: {node}")
            return Integer(maybe_int)

        if head == "ff.add":
            args = [_expr(a) for a in node[1:]]
            if not args:
                raise ValueError("ff.add requires at least one argument")
            return _fold_left(Operator.ADD, args) if len(args) > 1 else args[0]

        if head == "ff.mul":
            args = [_expr(a) for a in node[1:]]
            if not args:
                raise ValueError("ff.mul requires at least one argument")
            return _fold_left(Operator.MUL, args) if len(args) > 1 else args[0]

        if head == "ff.neg":
            if len(node) != 2:
                raise ValueError("ff.neg expects exactly one argument")
            return UnaryExpression(Operator.SUB, _expr(node[1]))

        if head == "=":
            if len(node) != 3:
                raise ValueError("= expects exactly two arguments")
            return BinaryExpression(Operator.EQU, _expr(node[1]), _expr(node[2]))

        raise ValueError(f"Unsupported QF_FF operator: {head}")

    for form in forms:
        if not form:
            continue
        head = form[0]
        if head == "set-logic":
            continue
        if head == "define-sort":
            continue
        if head == "declare-fun":
            name = form[1]
            declared.add(name)
            if name.endswith(FUSION_SUFFIX):
                outputs.append(
                    FusedVariable(name, VariableType.FIELD, _infer_sum_fusion(name))
                )
            else:
                inputs.append(Variable(name, VariableType.FIELD))
            continue
        if head == "define-fun":
            raise NotImplementedError("define-fun is not supported in QF_FF parser")
        if head == "assert":
            if len(form) != 2:
                raise ValueError("assert expects a single argument")
            expr = _expr(form[1])
            assertions.append(Assertion(identifier=f"assert_{len(assertions)}", value=expr))
            continue
        # ignore check-sat and other commands

    return Circuit(
        name="smtlib2_ff",
        inputs=inputs,
        outputs=outputs,
        statements=assertions,
    )


def parse_smtlib2(smtlib2: str, solver: str = "z3") -> Circuit:
    """
    Auto-detect SMT-LIB logic and parse into Circuit IR.
    """
    if re.search(r"\(set-logic\s+QF_FF\b", smtlib2):
        return parse_smtlib2_ff(smtlib2)
    return parse_smtlib2_core(smtlib2, solver=solver)
