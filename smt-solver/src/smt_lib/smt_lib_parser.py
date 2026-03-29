from io import StringIO
from typing import Dict, List, Tuple

from src.smt_lib.zk_ir import (
    Circuit,
    Assertion,
    Expression,
    FusedVariable,
    Variable,
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
