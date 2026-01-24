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

_FUSED_USE_SUB_RE = re.compile(
    r"\(\s*-\s*\(\s*-\s*(?P<fused>[^\s\)]+)\s+(?P<var>[^\s\)]+)\s*\)"
)
_FUSED_USE_DIV_RE = re.compile(
    r"\(\s*div\s+(?P<fused>[^\s\)]+)\s+(?P<var>[^\s\)]+)\s*\)"
)

def _infer_fusion_formula(var_name: str, smtlib2: str) -> Expression:
    """
    Infer fusion expression for a fused variable like:
        scr1_x5_plus_scr2_x3_minus_fused

    Heuristic (as you specified):
      - Parse the two source variables from the fused name by stripping "_fused"
        and splitting into [<var1>, <var2>] at the boundary between "..._plus"
        or "..._minus" and the next "scr..." prefix.

      - Then detect how the fused var is used in SMT-LIB:
          * if used as:   (- fused other)   (i.e. pattern "(- fused v)" inside a subtraction chain)
            -> fused = v1 + v2
          * if used as:   (div fused other)
            -> fused = v1 * v2

      - If we cannot detect usage, default to SUM (conservative).
    """

    if not var_name.endswith(FUSION_SUFFIX):
        raise ValueError(f"Expected fused variable name ending with '{FUSION_SUFFIX}', got: {var_name}")

    base = var_name[: -len(FUSION_SUFFIX)]  # strip "_fused"

    # ----------------------------
    # 1) Extract the two variables from the fused name
    # ----------------------------
    # We look for the second variable starting at the second "scr" occurrence.
    # This matches your examples: scr1_..._scr2_...
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


    # ----------------------------
    # 2) Determine fusion kind from how it is used
    # ----------------------------
    # Look for patterns that clearly indicate whether the fused var participates
    # in subtraction form "(- fused X)" or division form "(div fused X)".
    # We also validate the "other" variable equals one of var1/var2.
    kind = None  # "sum" | "prod"

    for m in _FUSED_USE_SUB_RE.finditer(smtlib2):
        fused = m.group("fused")
        if fused != var_name:
            continue
        other = m.group("var")
        if other == var1 or other == var2:
            kind = "sum"
            break

    if kind is None:
        for m in _FUSED_USE_DIV_RE.finditer(smtlib2):
            fused = m.group("fused")
            if fused != var_name:
                continue
            other = m.group("var")
            if other == var1 or other == var2:
                kind = "prod"
                break
    
    # Default if we can't find usage (still return *something* deterministic)
    if kind is None:
        kind = "sum"

    # ----------------------------
    # 3) Build the IR expression
    # ----------------------------
    a = Variable(var1, VariableType.FIELD)
    b = Variable(var2, VariableType.FIELD)

    if kind == "sum":
        return BinaryExpression(Operator.ADD, a, b)
    if kind == "prod":
        return BinaryExpression(Operator.MUL, a, b)

    raise AssertionError("unreachable")

# ------------------------------------------------------------
# Main parser function
# ------------------------------------------------------------

def parse_smtlib2_core(smtlib2: str, solver: str = "z3") -> Circuit:
    """
    Parse SMT-LIB v2 in the (QF_)LIA fragment:
      sorts: Bool, Int
      ops: core boolean + LIA arithmetic/comparisons
      supports let by inlining (substitution via environment).
    Assumption: benchmarks are well-formed (no extra typechecking/guards).
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
    from pysmt.typing import BOOL

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

            if name.endswith(FUSION_SUFFIX):
                outputs.append(
                    FusedVariable(
                        name,
                        vtype,
                        _infer_fusion_formula(name, smtlib2),  # placeholder
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

                if node.symbol_type() == BOOL:
                    return Variable(name, VariableType.BOOLEAN)
                return Variable(name, VariableType.FIELD)  # Ints are cast to Field

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
