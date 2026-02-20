from io import StringIO
from typing import Dict, List, Tuple
import re

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
    Integer,
)

FUSION_SUFFIX = "_fused"

# ------------------------------------------------------------
# Preprocess: make PySMT accept SMT-LIB files that use `div`
# by declaring it as an uninterpreted function (only if needed).
# ------------------------------------------------------------

_DIV_DECL_RE = re.compile(
    r"\(\s*declare-fun\s+div\s+\(\s*Int\s+Int\s*\)\s+Int\s*\)"
)

def preprocess_div_as_uf(smt2: str) -> str:
    # Fast path: no div token
    if "div" not in smt2:
        return smt2

    # If already declared, do nothing
    if _DIV_DECL_RE.search(smt2):
        return smt2

    decl = "(declare-fun div (Int Int) Int)\n"

    # Insert after (set-logic ...) if present, else at top
    m = re.search(r"\(\s*set-logic\b[^\)]*\)\s*", smt2)
    if m:
        return smt2[:m.end()] + "\n" + decl + smt2[m.end():]
    return decl + smt2


# ------------------------------------------------------------
# Fusion formula inference
# ------------------------------------------------------------

def _infer_fusion_formula(var_name: str, smtlib2: str) -> Expression:
    """
    TEMPORARY HACK (TODO): Always infer XOR fusion for fused variables.

    Semantics enforced:
      fused = xor(var1, var2)
    """

    if not var_name.endswith(FUSION_SUFFIX):
        raise ValueError(
            f"Expected fused variable name ending with '{FUSION_SUFFIX}', got: {var_name}"
        )

    # Parse var1/var2 from name
    # Format after pruning: var1__var2__orig__<original>_fused
    # Original format: var1_var2_fused (where var1/var2 contain underscores)
    base = var_name[: -len(FUSION_SUFFIX)]
    
    # Check if this is a renamed fused variable (contains __)
    if "__" in base:
        parts = base.split("__")
        if len(parts) >= 2:
            var1 = parts[0]
            var2 = parts[1]
        else:
            raise ValueError(f"Cannot parse renamed fused name: {var_name}")
    else:
        # Original fused variable format: find second "scr"
        first = base.find("scr")
        if first == -1:
            raise ValueError(f"Cannot parse fused name (no 'scr'): {var_name}")
        second = base.find("scr", first + 1)
        if second == -1:
            raise ValueError(f"Cannot parse fused name (no second 'scr'): {var_name}")

        var1 = base[:second]
        var2 = base[second:]
        if var1.endswith("_"):
            var1 = var1[:-1]

    # Handle literal boolean values in component names (from pruning)
    if var1 == "true":
        a = Boolean(True)
    elif var1 == "false":
        a = Boolean(False)
    else:
        a = Variable(var1, VariableType.BOOLEAN)
    
    if var2 == "true":
        b = Boolean(True)
    elif var2 == "false":
        b = Boolean(False)
    else:
        b = Variable(var2, VariableType.BOOLEAN)
    return BinaryExpression(Operator.LXOR, a, b)


# ------------------------------------------------------------
# Main parser function
# ------------------------------------------------------------

def parse_smtlib2_core(smtlib2: str, solver: str = "z3") -> Circuit:
    """
    Parse SMT-LIB v2 in the (QF_)LIA fragment:
      sorts: Bool, Int
      ops: core boolean + LIA arithmetic/comparisons
      supports let by inlining (substitution via environment).

    IMPORTANT SIMPLIFICATION:
      All variables are forced to be VariableType.BOOLEAN, regardless of SMT sort.
      (No declaration sort inspection; SYMBOLs always become boolean vars.)
    """

    if solver == "cvc5":
        # ------------------------------------------------------------------
        # THIS IMPORT NEEDS TO STAY TO AVOID PROBLEMS BETWEEN PYSMT AND CVC5
        import cvc5.pythonic
        # ------------------------------------------------------------------

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

    # ---- preprocess BEFORE parsing ----
    smtlib2 = preprocess_div_as_uf(smtlib2)
    script, assertions = parse_smtlib2_to_pysmt_ir(smtlib2)

    # Inputs from declare-fun
    inputs: List[Variable] = []
    outputs: List[Variable] = []

    for cmd in script.commands:
        if cmd.name == "declare-fun":
            name = str(cmd.args[0])

            # Skip helper UF we might inject
            if name == "div":
                continue

            # FORCE: everything is boolean
            vtype = VariableType.BOOLEAN

            if name.endswith(FUSION_SUFFIX):
                outputs.append(
                    FusedVariable(
                        name,
                        vtype,
                        _infer_fusion_formula(name, smtlib2),
                    )
                )
            else:
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
            # ----- symbols / constants -----
            case op.SYMBOL:
                name = node.symbol_name()
                if name in env:
                    return env[name]

                # FORCE: every symbol is a boolean variable (even if SMT sort is Int).
                return Variable(name, VariableType.BOOLEAN)

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
            # NOTE: We do not typecheck; symbols are boolean-typed but can still appear here.
            case op.PLUS:
                args = [fnode_to_zkir(a, env) for a in node.args()]
                return fold_left(Operator.ADD, args)

            case op.MINUS:
                args = list(node.args())
                if len(args) == 1:
                    return UnaryExpression(Operator.NEG, fnode_to_zkir(args[0], env))
                zargs = [fnode_to_zkir(a, env) for a in args]
                return fold_left(Operator.SUB, zargs)

            case op.TIMES:
                args = [fnode_to_zkir(a, env) for a in node.args()]
                return fold_left(Operator.MUL, args)

            # ----- LIA comparisons -----
            case op.LT:
                return BinaryExpression(
                    Operator.LTH,
                    fnode_to_zkir(node.arg(0), env),
                    fnode_to_zkir(node.arg(1), env),
                )

            case op.LE:
                return BinaryExpression(
                    Operator.LEQ,
                    fnode_to_zkir(node.arg(0), env),
                    fnode_to_zkir(node.arg(1), env),
                )

            # ----- function applications (UF) -----
            case op.FUNCTION:
                fname = node.function_name()
                fstr = fname.symbol_name() if hasattr(fname, "symbol_name") else str(fname)
                args = [fnode_to_zkir(a, env) for a in node.args()]

                if fstr == "div":
                    if len(args) != 2:
                        raise NotImplementedError(f"(div ...) with arity != 2: {node}")
                    return BinaryExpression(Operator.DIV, args[0], args[1])

                raise NotImplementedError(f"Unsupported function application: {fstr} ({node})")

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
