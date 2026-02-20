# -----------------------------
# zokrates/nodes.py
# -----------------------------
from __future__ import annotations
from dataclasses import dataclass, field

# Base
@dataclass
class ASTNode:
    def copy(self):
        raise NotImplementedError()

@dataclass
class Expression(ASTNode):
    def copy(self):
        raise NotImplementedError()

@dataclass
class Statement(ASTNode):
    def copy(self):
        raise NotImplementedError()

# Expressions
@dataclass
class Identifier(Expression):
    name: str
    def copy(self) -> "Identifier":
        return Identifier(self.name)

@dataclass
class Literal(Expression):
    value: int | bool | str
    def copy(self) -> "Literal":
        return Literal(self.value)

@dataclass
class UnaryExpression(Expression):
    op: str
    value: Expression
    def copy(self) -> "UnaryExpression":
        return UnaryExpression(self.op, self.value.copy())

@dataclass
class BinaryExpression(Expression):
    op: str
    lhs: Expression
    rhs: Expression
    def copy(self) -> "BinaryExpression":
        return BinaryExpression(self.op, self.lhs.copy(), self.rhs.copy())

@dataclass
class ConditionalExpression(Expression):
    """
    if <cond> { <then_expr> } else { <else_expr> }
    """
    cond: Expression
    then_expr: Expression
    else_expr: Expression
    def copy(self) -> "ConditionalExpression":
        return ConditionalExpression(self.cond.copy(), self.then_expr.copy(), self.else_expr.copy())

@dataclass
class IndexAccess(Expression):
    base: Expression
    index: Expression
    def copy(self) -> "IndexAccess":
        return IndexAccess(self.base.copy(), self.index.copy())

@dataclass
class CallExpression(Expression):
    name: str
    args: list[Expression] = field(default_factory=list)
    def copy(self) -> "CallExpression":
        return CallExpression(self.name, [a.copy() for a in self.args])

# Statements
@dataclass
class LetStatement(Statement):
    """
    field mut x = 0;
    """
    type_name: str               # "field", "u32", "bool", ...
    name: Identifier
    expr: Expression
    is_mut: bool = False
    def copy(self) -> "LetStatement":
        return LetStatement(self.type_name, self.name.copy(), self.expr.copy(), self.is_mut)

@dataclass
class AssignStatement(Statement):
    lhs: Expression
    rhs: Expression
    def copy(self) -> "AssignStatement":
        return AssignStatement(self.lhs.copy(), self.rhs.copy())

@dataclass
class AssertStatement(Statement):
    cond: Expression
    def copy(self) -> "AssertStatement":
        return AssertStatement(self.cond.copy())

@dataclass
class ExprStatement(Statement):
    expr: Expression
    def copy(self) -> "ExprStatement":
        return ExprStatement(self.expr.copy())

@dataclass
class ReturnStatement(Statement):
    value: Expression | None = None
    def copy(self) -> "ReturnStatement":
        return ReturnStatement(self.value.copy() if self.value else None)

@dataclass
class ForLoop(Statement):
    """
    for u32 i in 0..N { ... }
    """
    index_name: str
    start: Expression
    end: Expression
    body: list[Statement]
    def copy(self) -> "ForLoop":
        return ForLoop(self.index_name, self.start.copy(), self.end.copy(), [s.copy() for s in self.body])

# Function / Document
@dataclass
class Parameter(ASTNode):
    """
    (private) field x
    """
    type_name: str
    name: str
    is_private: bool = False
    def copy(self) -> "Parameter":
        return Parameter(self.type_name, self.name, self.is_private)

@dataclass
class Function(ASTNode):
    name: str
    params: list[Parameter]
    return_type: str | None          # e.g. "field" or "(field, field)" or "field[2]"
    body: list[Statement]
    def copy(self) -> "Function":
        return Function(
            self.name,
            [p.copy() for p in self.params],
            self.return_type,
            [s.copy() for s in self.body],
        )

@dataclass
class Document(ASTNode):
    main: Function
    def copy(self) -> "Document":
        return Document(self.main.copy())
