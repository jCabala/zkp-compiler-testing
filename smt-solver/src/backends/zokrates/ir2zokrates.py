from __future__ import annotations

from dataclasses import dataclass

import src.smt_lib.zk_ir as IRNodes

from .nodes import *


BN254_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617


@dataclass
class ZokratesConfig:
    private_inputs: set[str] | None = None
    prime: int = BN254_PRIME


class IR2ZokratesVisitor:
    def __init__(self, config: ZokratesConfig | None = None):
        self.cfg = config or ZokratesConfig()
        self._outputs: set[str] = set()

    def transform(self, system: IRNodes.Circuit) -> Document:
        return self.visit_circuit(system)

    def _field_lit(self, n: int) -> Literal:
        return Literal(f"{int(n) % self.cfg.prime}f")

    def _type_from_var(self, var: IRNodes.Variable) -> str:
        if var.variable_type == IRNodes.VariableType.BOOLEAN:
            return "bool"
        return "field"

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

    def visit_variable(self, node: IRNodes.Variable) -> tuple[Expression, list[Statement]]:
        return Identifier(node.name), []

    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        return Literal(bool(node.value)), []

    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        return self._field_lit(node.value), []

    def visit_unary(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        value, tail = self.visit_expression(node.value)

        if node.op == IRNodes.Operator.SUB:
            return UnaryExpression("-", value), tail

        if node.op == IRNodes.Operator.NOT:
            return UnaryExpression("!", value), tail

        raise NotImplementedError(f"unary op {node.op.value}")

    def visit_binary(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        op = node.op
        if op == IRNodes.Operator.ADD:
            return BinaryExpression("+", lhs, rhs), statements
        if op == IRNodes.Operator.SUB:
            return BinaryExpression("-", lhs, rhs), statements
        if op == IRNodes.Operator.MUL:
            return BinaryExpression("*", lhs, rhs), statements
        if op == IRNodes.Operator.DIV:
            return BinaryExpression("/", lhs, rhs), statements
        if op == IRNodes.Operator.POW:
            return BinaryExpression("**", lhs, rhs), statements

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
            return cmp_expr, statements

        if op == IRNodes.Operator.LAND:
            return BinaryExpression("&&", lhs, rhs), statements

        if op == IRNodes.Operator.LOR:
            return BinaryExpression("||", lhs, rhs), statements

        if op == IRNodes.Operator.LXOR:
            return BinaryExpression("^", lhs, rhs), statements

        if op == IRNodes.Operator.AND:
            return BinaryExpression("&", lhs, rhs), statements
        if op == IRNodes.Operator.OR:
            return BinaryExpression("|", lhs, rhs), statements
        if op == IRNodes.Operator.XOR:
            return BinaryExpression("^", lhs, rhs), statements

        raise NotImplementedError(f"binary op {op.value}")

    def visit_ternary(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []
        cond, cond_tail = self.visit_expression(node.condition)
        statements += cond_tail
        if_expr, if_tail = self.visit_expression(node.if_expr)
        statements += if_tail
        else_expr, else_tail = self.visit_expression(node.else_expr)
        statements += else_tail

        return ConditionalExpression(cond, if_expr, else_expr), statements

    def _assert_expr(self, expr: Expression) -> Statement:
        return AssertStatement(expr)

    def visit_assertion(self, node: IRNodes.Assertion) -> list[Statement]:
        expr, tail = self.visit_expression(node.value)
        return tail + [self._assert_expr(expr)]

    def visit_assume(self, node: IRNodes.Assume) -> list[Statement]:
        expr, tail = self.visit_expression(node.condition)
        return tail + [self._assert_expr(expr)]

    def visit_assignment(self, node: IRNodes.Assignment) -> list[Statement]:
        lhs, lhs_tail = self.visit_expression(node.lhs)
        rhs, rhs_tail = self.visit_expression(node.rhs)
        if isinstance(node.lhs, IRNodes.Variable) and node.lhs.name in self._outputs:
            return lhs_tail + rhs_tail + [AssertStatement(BinaryExpression("==", lhs, rhs))]
        return lhs_tail + rhs_tail + [AssignStatement(lhs, rhs)]

    def visit_circuit(self, node: IRNodes.Circuit) -> Document:
        self._outputs = {out.name for out in node.outputs}
        private_inputs = self.cfg.private_inputs
        if private_inputs is None:
            private_inputs = {inp.name for inp in node.inputs}

        params = [
            Parameter(self._type_from_var(inp), inp.name, is_private=(inp.name in private_inputs))
            for inp in node.inputs
        ] + [
            Parameter(self._type_from_var(out), out.name, is_private=False)
            for out in node.outputs
        ]

        body: list[Statement] = []

        for stmt in node.statements:
            body += self.visit_statement(stmt)

        if len(node.outputs) == 0:
            body.append(ReturnStatement(None))
            return_type: str | None = None
        elif len(node.outputs) == 1:
            body.append(ReturnStatement(Identifier(node.outputs[0].name)))
            return_type = self._type_from_var(node.outputs[0])
        else:
            n_outputs = len(node.outputs)
            first_type = self._type_from_var(node.outputs[0])
            return_type = f"{first_type}[{n_outputs}]"
            outputs_expr = [Identifier(out.name) for out in node.outputs]
            body.append(
                LetStatement(
                    return_type,
                    Identifier("outs"),
                    CallExpression("__array_lit__", outputs_expr),
                )
            )
            body.append(ReturnStatement(Identifier("outs")))

        return Document(Function("main", params, return_type, body))
