from io import StringIO
from typing import List, Tuple

from pysmt.smtlib.parser import SmtLibParser
from pysmt.fnode import FNode
from pysmt.smtlib.script import SmtLibScript

from src.smt_lib.zk_ir import Circuit, Assertion, Expression, Variable, Boolean, UnaryExpression, BinaryExpression, Operator, VariableType
from pysmt import operators as op
from pysmt.typing import BOOL

def parse_smtlib2_core(
    smtlib2: str,
) -> Circuit:
    """
    Parse an SMT-LIB v2 core theory string into.
    Args:
        smtlib2: SMT-LIB v2 input as a string.
    Returns:
        zk_ir.Circuit: The parsed circuit representation.
    """
    script, assertions = parse_smtlib2_to_pysmt_ir(smtlib2)

    # Collect declared variables (for inputs)
    inputs = []
    outputs = []
    for cmd in script.commands:
        if cmd.name == "declare-fun":
            var_name = cmd.args[0]
            inputs.append(Variable(str(var_name), VariableType.BOOLEAN))
        elif cmd.name == "define-fun":
            raise NotImplementedError("define-fun is not supported in SMT-LIB core parser")

    # Helper: Recursively convert PySMT FNode to zk_ir Expression
    def fnode_to_zkir(node: FNode) -> Expression:
        nt = node.node_type()

        match nt:
            case op.SYMBOL:
                t = node.symbol_type()
                if t != BOOL:
                    raise NotImplementedError(f"Unsupported symbol type: {t} ({node})")
                return Variable(node.symbol_name(), VariableType.BOOLEAN)

            case op.BOOL_CONSTANT:
                return Boolean(bool(node.constant_value()))

            case op.NOT:
                return UnaryExpression(Operator.NOT, fnode_to_zkir(node.arg(0)))

            case op.AND:
                # AND is n-ary in PySMT, so don't assume 2 args
                args = [fnode_to_zkir(a) for a in node.args()]
                # fold into binary if your IR is binary
                expr = args[0]
                for a in args[1:]:
                    expr = BinaryExpression(Operator.LAND, expr, a)
                return expr

            case op.OR:
                args = [fnode_to_zkir(a) for a in node.args()]
                expr = args[0]
                for a in args[1:]:
                    expr = BinaryExpression(Operator.LOR, expr, a)
                return expr

            case op.IMPLIES:
                return BinaryExpression(
                    Operator.LOR,
                    UnaryExpression(Operator.NOT, fnode_to_zkir(node.arg(0))),
                    fnode_to_zkir(node.arg(1)),
                )

            case op.IFF:
                return BinaryExpression(Operator.EQU,
                                    fnode_to_zkir(node.arg(0)),
                                    fnode_to_zkir(node.arg(1)))

            case op.EQUALS:
                return BinaryExpression(Operator.EQU,
                                    fnode_to_zkir(node.arg(0)),
                                    fnode_to_zkir(node.arg(1)))

            case _:
                raise NotImplementedError(f"Unsupported node type: {nt} ({node})")

    # Convert each assertion to a zk_ir Assertion
    statements = []
    for idx, fnode in enumerate(assertions):
        expr = fnode_to_zkir(fnode)
        assertion = Assertion(identifier=f"assert_{idx}", value=expr)
        statements.append(assertion)

    # Build Circuit IR
    circuit = Circuit(
        name="smtlib2_core",
        inputs=inputs,
        outputs=outputs,
        statements=statements
    )

    return circuit

def parse_smtlib2_to_pysmt_ir(
    smtlib2: str,
) -> Tuple[SmtLibScript, List[FNode]]:
    """
    Parse an SMT-LIB v2 string into PySMT IR.

    Args:
        smtlib2: SMT-LIB v2 input as a string.

    Returns:
        script: SmtLibScript (script-level IR, sequence of commands)
        assertions: List of FNode objects (formula-level IR for each assert)
    """
    parser = SmtLibParser()
    script = parser.get_script(StringIO(smtlib2))

    assertions: List[FNode] = []
    for cmd in script.commands:
        if cmd.name == "assert":
            # The asserted formula is the first argument
            assertions.append(cmd.args[0])

    return script, assertions