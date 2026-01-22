from io import StringIO
import os
from typing import Dict, List, Tuple

from src.smt_lib.zk_ir import (
    Circuit,
    Assertion,
    Expression,
    Variable,
    Boolean,
    UnaryExpression,
    BinaryExpression,
    Operator,
    VariableType,
    Integer,  # assumes you have an Integer literal node in your IR
)

def parse_smtlib2_core(smtlib2: str, solver: str = "z3") -> Circuit:
    """
    Parse SMT-LIB v2 in the (QF_)LIA fragment:
      sorts: Bool, Int
      ops: core boolean + LIA arithmetic/comparisons
      supports let by inlining (substitution via environment).
    Assumption: benchmarks are well-formed (no extra typechecking/guards).
    """

    if solver == "cvc5":
        # --------------------
        # THIS IMPORT NEEDS TO STAY TO AVOID PROBLEMS BETWEEN PYSMT AND CVC5
        import cvc5.pythonic
        # --------------------

    from pysmt.smtlib.parser import SmtLibParser
    from pysmt.fnode import FNode
    from pysmt.smtlib.script import SmtLibScript
    from pysmt import operators as op
    from pysmt.typing import BOOL

    def parse_smtlib2_to_pysmt_ir(smtlib2: str) -> Tuple[SmtLibScript, List[FNode]]:
        parser = SmtLibParser()
        script = parser.get_script(StringIO(smtlib2))

        assertions: List[FNode] = []
        for cmd in script.commands:
            if cmd.name == "assert":
                assertions.append(cmd.args[0])

        return script, assertions

    script, assertions = parse_smtlib2_to_pysmt_ir(smtlib2)

    # Inputs from declare-fun
    inputs: List[Variable] = []
    outputs: List[Variable] = []

    for cmd in script.commands:
        if cmd.name == "declare-fun":
            name = str(cmd.args[0])

            # In LIA: only Bool or Int. Infer Bool if declared sort is Bool, else Int.
            vtype = VariableType.FIELD
            if len(cmd.args) >= 3:
                sort = cmd.args[2]
                if sort == "Bool" or sort == BOOL:
                    vtype = VariableType.BOOLEAN
            elif len(cmd.args) >= 2:
                sort = cmd.args[1]
                if sort == "Bool" or sort == BOOL:
                    vtype = VariableType.BOOLEAN

            inputs.append(Variable(name, vtype))

        elif cmd.name == "define-fun":
            raise NotImplementedError("define-fun is not supported in this parser")

    def fold_left(opcode: Operator, exprs: List[Expression]) -> Expression:
        out = exprs[0]
        for e in exprs[1:]:
            out = BinaryExpression(opcode, out, e)
        return out

    def fnode_to_zkir(node: FNode, env: Dict[str, Expression] | None = None) -> Expression:
        """
        env implements SMT-LIB let via substitution.
        """
        if env is None:
            env = {}

        nt = node.node_type()

        match nt:
            # # ----- let -----
            # case op.LET:
            #     # SMT-LIB let is simultaneous binding:
            #     # (let ((x t1) (y t2)) body)
            #     # RHS are evaluated in the *outer* env.
            #     bind_syms = node.let_variables()
            #     bind_vals = node.let_values()
            #     body = node.let_body()

            #     new_bindings: Dict[str, Expression] = {}
            #     for s, v in zip(bind_syms, bind_vals):
            #         # s is a Symbol FNode; get its name
            #         new_bindings[s.symbol_name()] = fnode_to_zkir(v, env)

            #     # Extend env for body
            #     env2 = dict(env)
            #     env2.update(new_bindings)
            #     return fnode_to_zkir(body, env2)

            # ----- symbols / constants -----
            case op.SYMBOL:
                name = node.symbol_name()
                if name in env:
                    return env[name]

                # LIA assumption: only Bool and Int.
                if node.symbol_type() == BOOL:
                    return Variable(name, VariableType.BOOLEAN)
                return Variable(name, VariableType.FIELD) # Ints are cast to Field

            case op.BOOL_CONSTANT:
                return Boolean(bool(node.constant_value()))

            case op.INT_CONSTANT:
                return Integer(int(node.constant_value()))

            # ----- boolean core -----
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

            # ----- LIA arithmetic -----
            case op.PLUS:
                args = [fnode_to_zkir(a, env) for a in node.args()]
                return fold_left(Operator.ADD, args)

            case op.MINUS:
                # unary (- x) or n-ary (- a b c) = ((a-b)-c)
                args = list(node.args())
                if len(args) == 1:
                    return UnaryExpression(Operator.NEG, fnode_to_zkir(args[0], env))
                zargs = [fnode_to_zkir(a, env) for a in args]
                return fold_left(Operator.SUB, zargs)

            case op.TIMES:
                # In LIA benchmarks, this should be linear (* c t), but we assume correctness.
                args = [fnode_to_zkir(a, env) for a in node.args()]
                return fold_left(Operator.MUL, args)

            # ----- LIA comparisons -----
            case op.LT:
                return BinaryExpression(Operator.LTH, fnode_to_zkir(node.arg(0), env), fnode_to_zkir(node.arg(1), env))

            case op.LE:
                return BinaryExpression(Operator.LEQ, fnode_to_zkir(node.arg(0), env), fnode_to_zkir(node.arg(1), env))

            case op.GT:
                return BinaryExpression(Operator.GTH, fnode_to_zkir(node.arg(0), env), fnode_to_zkir(node.arg(1), env))

            case op.GE:
                return BinaryExpression(Operator.GEQ, fnode_to_zkir(node.arg(0), env), fnode_to_zkir(node.arg(1), env))

            case _:
                raise NotImplementedError(f"Unsupported node type: {nt} ({node})")

    statements: List[Assertion] = []
    for idx, fnode in enumerate(assertions):
        expr = fnode_to_zkir(fnode)
        statements.append(Assertion(identifier=f"assert_{idx}", value=expr))

    return Circuit(
        name="smtlib2_lia",
        inputs=inputs,
        outputs=outputs,
        statements=statements,
    )

