# -----------------------------
# zokrates/visitor.py
# -----------------------------
from __future__ import annotations

from dataclasses import dataclass
from circuzz.common.field import CurvePrime
from circuzz.ir import nodes as IRNodes

from .nodes import *


@dataclass
class ZokratesConfig:
    # If True: represent booleans as field elements 0/1 (matches gnark-ish style)
    bool_as_field: bool = True
    # Mark which inputs are private; default: all private
    private_inputs: set[str] | None = None
    test_iterations: int = 2
    boundary_input_probability: float = 0.1

    @classmethod
    def from_dict(cls, value: dict) -> 'ZokratesConfig':
        bool_as_field = bool(value.get("bool_as_field", True))
        private_inputs = value.get("private_inputs", None)
        test_iterations = int(value.get("test_iterations", 2))
        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        if private_inputs is not None:
            private_inputs = set(private_inputs)
        return ZokratesConfig(
            bool_as_field=bool_as_field,
            private_inputs=private_inputs,
            test_iterations=test_iterations,
            boundary_input_probability=boundary_input_probability,
        )


class IR2ZokratesVisitor:
    """
    IR -> ZoKrates AST (nodes.py).

    Key ZoKrates rules handled here:
      - Mutable locals use `_mut` (emitter prints it when is_mut=True).
      - Field literals are emitted as string tokens "0f", "1f", ...
      - If bool_as_field=True:
          * boolean constants are 0f/1f
          * comparisons produce 0f/1f via if-then-else
          * assertions require expr == 1f
          * ternary condition is treated as (cond == 1f)
      - Multiple outputs are returned as field[n] array.
      - Output locals are ALWAYS declared mutable because IR assignments may target them.
    """

    def __init__(self, config: ZokratesConfig | None = None, prime: CurvePrime = CurvePrime.BN254):
        self.cfg = config or ZokratesConfig()
        self._outputs: set[str] = set()
        self.prime = prime

    # -------------------------
    # Entry
    # -------------------------
    def transform(self, system: IRNodes.Circuit) -> Document:
        return self.visit_circuit(system)

    # -------------------------
    # Helpers
    # -------------------------
    def _field_lit(self, n: int) -> Literal:
        # ZoKrates field literals are like `0f`, `1f`, ...
        return Literal(f"{int(n)}f")

    def _bool_true(self) -> Literal:
        return self._field_lit(1) if self.cfg.bool_as_field else Literal(True)

    def _bool_false(self) -> Literal:
        return self._field_lit(0) if self.cfg.bool_as_field else Literal(False)

    # -------------------------
    # Dispatch
    # -------------------------
    def visit_expression(self, node: IRNodes.IRNode) -> tuple[Expression, list[Statement]]:
        match node:
            case IRNodes.Variable():
                return self.visit_variable(node)
            case IRNodes.Boolean():
                return self.visit_boolean(node)
            case IRNodes.Integer():
                return self.visit_integer(node)
            case IRNodes.UnaryExpression():
                return self.visit_unary(node)
            case IRNodes.BinaryExpression():
                return self.visit_binary(node)
            case IRNodes.TernaryExpression():
                return self.visit_ternary(node)
            case _:
                raise NotImplementedError(f"expr node: {node.__class__}")

    def visit_statement(self, node: IRNodes.IRNode) -> list[Statement]:
        match node:
            case IRNodes.Assertion():
                return self.visit_assertion(node)
            case IRNodes.Assignment():
                return self.visit_assignment(node)
            case IRNodes.Assume():
                return self.visit_assume(node)
            case _:
                raise NotImplementedError(f"stmt node: {node.__class__}")

    # -------------------------
    # Leaves
    # -------------------------
    def visit_variable(self, node: IRNodes.Variable) -> tuple[Expression, list[Statement]]:
        return Identifier(node.name), []

    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        if self.cfg.bool_as_field:
            return self._field_lit(1 if node.value else 0), []
        return Literal(bool(node.value)), []

    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        # ZoKrates distinguishes {integer} and field. In circuits, we want field constants.
        # Emit as field literals with `f` suffix.
        # All field literals must be < prime
        value = int(node.value) % self.prime.value
        return Literal(f"{value}f"), []

    # -------------------------
    # Expressions
    # -------------------------
    def visit_unary(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        val, tail = self.visit_expression(node.value)

        if node.op == IRNodes.Operator.SUB:
            return UnaryExpression("-", val), tail

        if node.op == IRNodes.Operator.NOT:
            if self.cfg.bool_as_field:
                # NOT on field-bool: if x == 0f then 1f else 0f
                return (
                    ConditionalExpression(
                        BinaryExpression("==", val, self._field_lit(0)),
                        self._field_lit(1),
                        self._field_lit(0),
                    ),
                    tail,
                )
            return UnaryExpression("!", val), tail

        raise NotImplementedError(f"unary op {node.op.value}")

    def visit_binary(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        stmts: list[Statement] = []
        lhs, lt = self.visit_expression(node.lhs)
        stmts += lt
        rhs, rt = self.visit_expression(node.rhs)
        stmts += rt

        op = node.op

        # Arithmetic
        if op == IRNodes.Operator.ADD:
            return BinaryExpression("+", lhs, rhs), stmts
        if op == IRNodes.Operator.SUB:
            return BinaryExpression("-", lhs, rhs), stmts
        if op == IRNodes.Operator.MUL:
            return BinaryExpression("*", lhs, rhs), stmts
        if op == IRNodes.Operator.DIV:
            return BinaryExpression("/", lhs, rhs), stmts
        if op == IRNodes.Operator.POW:
            return BinaryExpression("**", lhs, rhs), stmts

        # Comparisons / equality
        if op in (
            IRNodes.Operator.EQU,
            IRNodes.Operator.NEQ,
            IRNodes.Operator.LTH,
            IRNodes.Operator.LEQ,
            IRNodes.Operator.GTH,
            IRNodes.Operator.GEQ,
        ):
            op_map = {
                IRNodes.Operator.EQU: "==",
                IRNodes.Operator.NEQ: "!=",
                IRNodes.Operator.LTH: "<",
                IRNodes.Operator.LEQ: "<=",
                IRNodes.Operator.GTH: ">",
                IRNodes.Operator.GEQ: ">=",
            }
            cmp_expr = BinaryExpression(op_map[op], lhs, rhs)
            if self.cfg.bool_as_field:
                return (
                    ConditionalExpression(cmp_expr, self._field_lit(1), self._field_lit(0)),
                    stmts,
                )
            return cmp_expr, stmts

        # Logical on 0/1 field-bools
        if op == IRNodes.Operator.LAND:
            if self.cfg.bool_as_field:
                # AND = a*b
                return BinaryExpression("*", lhs, rhs), stmts
            return BinaryExpression("&&", lhs, rhs), stmts

        if op == IRNodes.Operator.LOR:
            if self.cfg.bool_as_field:
                # OR = a + b - a*b
                return (
                    BinaryExpression(
                        "-",
                        BinaryExpression("+", lhs, rhs),
                        BinaryExpression("*", lhs, rhs),
                    ),
                    stmts,
                )
            return BinaryExpression("||", lhs, rhs), stmts

        if op == IRNodes.Operator.LXOR:
            if self.cfg.bool_as_field:
                # XOR = a + b - 2ab
                two_ab = BinaryExpression(
                    "*",
                    self._field_lit(2),
                    BinaryExpression("*", lhs, rhs),
                )
                return BinaryExpression("-", BinaryExpression("+", lhs, rhs), two_ab), stmts
            return BinaryExpression("^", lhs, rhs), stmts

        # Bitwise (kept as-is; may not be meaningful for all ZoKrates setups)
        if op == IRNodes.Operator.AND:
            return BinaryExpression("&", lhs, rhs), stmts
        if op == IRNodes.Operator.OR:
            return BinaryExpression("|", lhs, rhs), stmts
        if op == IRNodes.Operator.XOR:
            return BinaryExpression("^", lhs, rhs), stmts

        raise NotImplementedError(f"binary op {op.value}")

    def visit_ternary(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        stmts: list[Statement] = []
        cond, ct = self.visit_expression(node.condition)
        stmts += ct
        texpr, tt = self.visit_expression(node.if_expr)
        stmts += tt
        fexpr, ft = self.visit_expression(node.else_expr)
        stmts += ft

        if self.cfg.bool_as_field:
            # cond is 0/1 field-bool; treat true as == 1f
            cond_bool = BinaryExpression("==", cond, self._field_lit(1))
        else:
            cond_bool = cond

        return ConditionalExpression(cond_bool, texpr, fexpr), stmts

    # -------------------------
    # Statements
    # -------------------------
    def _assert_expr(self, expr: Expression) -> Statement:
        if self.cfg.bool_as_field:
            # assert(expr == 1f)
            return AssertStatement(BinaryExpression("==", expr, self._field_lit(1)))
        return AssertStatement(expr)

    def visit_assertion(self, node: IRNodes.Assertion) -> list[Statement]:
        expr, tail = self.visit_expression(node.value)
        return tail + [self._assert_expr(expr)]

    def visit_assume(self, node: IRNodes.Assume) -> list[Statement]:
        expr, tail = self.visit_expression(node.condition)
        return tail + [self._assert_expr(expr)]

    def visit_assignment(self, node: IRNodes.Assignment) -> list[Statement]:
        stmts: list[Statement] = []
        lhs, lt = self.visit_expression(node.lhs)
        stmts += lt
        rhs, rt = self.visit_expression(node.rhs)
        stmts += rt
        stmts.append(AssignStatement(lhs, rhs))
        return stmts

    # -------------------------
    # Circuit -> main()
    # -------------------------
    def visit_circuit(self, node: IRNodes.Circuit) -> Document:
        self._outputs = set(node.outputs)

        private_inputs = self.cfg.private_inputs
        if private_inputs is None:
            private_inputs = set(node.inputs)

        params = [
            Parameter("field", name, is_private=(name in private_inputs))
            for name in node.inputs
        ]

        body: list[Statement] = []

        # Declare outputs as MUTABLE locals initialized to 0f
        # (IR may assign into outputs)
        for out in node.outputs:
            body.append(LetStatement("field", Identifier(out), self._field_lit(0), is_mut=True))

        # Translate statements
        for st in node.statements:
            body += self.visit_statement(st)

        # Return
        if len(node.outputs) == 0:
            body.append(ReturnStatement(None))
            ret_ty: str | None = None
        elif len(node.outputs) == 1:
            body.append(ReturnStatement(Identifier(node.outputs[0])))
            ret_ty = "field"
        else:
            n = len(node.outputs)
            ret_ty = f"field[{n}]"
            outs_exprs = [Identifier(o) for o in node.outputs]
            # IMPORTANT: do NOT use a leading underscore in identifiers (ZoKrates rejects it)
            body.append(LetStatement(ret_ty, Identifier("outs"), CallExpression("__array_lit__", outs_exprs), is_mut=False))
            body.append(ReturnStatement(Identifier("outs")))

        fn = Function("main", params, ret_ty, body)
        return Document(fn)
