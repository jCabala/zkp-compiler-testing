from __future__ import annotations

import io

from .nodes import *


class EmitVisitor:
    def __init__(self):
        self.indent = 0
        self.buf = io.StringIO()

    def emit(self, node: ASTNode | None) -> str:
        self.indent = 0
        self.buf = io.StringIO()
        if node is None:
            self.writeln("def main() -> field {")
            self.indent += 4
            self.writeln("return 0f;")
            self.indent -= 4
            self.writeln("}")
            return self.buf.getvalue()
        self.visit(node)
        return self.buf.getvalue()

    @property
    def tabs(self) -> str:
        return " " * self.indent

    def writeln(self, s: str = ""):
        self.buf.write(self.tabs + s + "\n")

    def visit(self, node: ASTNode | None):
        if node is None:
            self.buf.write("0f")
            return

        match node:
            case Document():
                self.visit_document(node)
            case Function():
                self.visit_function(node)
            case Parameter():
                self.visit_parameter(node)
            case LetStatement():
                self.visit_let(node)
            case AssignStatement():
                self.visit_assign(node)
            case AssertStatement():
                self.visit_assert(node)
            case ExprStatement():
                self.visit_expr_stmt(node)
            case ReturnStatement():
                self.visit_return(node)
            case ForLoop():
                self.visit_for(node)
            case Identifier():
                self.buf.write(node.name)
            case Literal():
                self.visit_lit(node)
            case UnaryExpression():
                self.visit_unary(node)
            case BinaryExpression():
                self.visit_binary(node)
            case ConditionalExpression():
                self.visit_conditional(node)
            case IndexAccess():
                self.visit_index(node)
            case CallExpression():
                self.visit_call(node)
            case _:
                self.buf.write("0f")

    def visit_document(self, node: Document):
        self.visit(node.main)

    def visit_parameter(self, p: Parameter):
        if p.is_private:
            self.buf.write("private ")
        self.buf.write(f"{p.type_name} {p.name}")

    def visit_function(self, fn: Function):
        self.buf.write(f"def {fn.name}(")
        for idx, param in enumerate(fn.params):
            self.visit_parameter(param)
            if idx + 1 != len(fn.params):
                self.buf.write(", ")
        self.buf.write(")")
        if fn.return_type:
            self.buf.write(f" -> {fn.return_type}")
        self.buf.write(" {\n")

        self.indent += 4
        for stmt in fn.body:
            if stmt is None:
                continue
            self.visit(stmt)
            if not self.buf.getvalue().endswith("\n"):
                self.buf.write("\n")
        self.indent -= 4
        self.buf.write("}\n")

    def visit_let(self, stmt: LetStatement):
        self.buf.write(self.tabs + stmt.type_name)
        self.buf.write(" mut " if stmt.is_mut else " ")
        self.visit(stmt.name)
        self.buf.write(" = ")
        self.visit(stmt.expr)
        self.buf.write(";\n")

    def visit_assign(self, stmt: AssignStatement):
        self.buf.write(self.tabs)
        self.visit(stmt.lhs)
        self.buf.write(" = ")
        self.visit(stmt.rhs)
        self.buf.write(";\n")

    def visit_assert(self, stmt: AssertStatement):
        self.buf.write(self.tabs + "assert(")
        self.visit(stmt.cond)
        self.buf.write(");\n")

    def visit_expr_stmt(self, stmt: ExprStatement):
        self.buf.write(self.tabs)
        self.visit(stmt.expr)
        self.buf.write(";\n")

    def visit_return(self, stmt: ReturnStatement):
        if stmt.value is None:
            self.writeln("return;")
            return
        self.buf.write(self.tabs + "return ")
        self.visit(stmt.value)
        self.buf.write(";\n")

    def visit_for(self, stmt: ForLoop):
        self.buf.write(self.tabs + f"for u32 {stmt.index_name} in ")
        self.visit(stmt.start)
        self.buf.write("..")
        self.visit(stmt.end)
        self.buf.write(" {\n")
        self.indent += 4
        for body_stmt in stmt.body:
            if body_stmt is None:
                continue
            self.visit(body_stmt)
            if not self.buf.getvalue().endswith("\n"):
                self.buf.write("\n")
        self.indent -= 4
        self.buf.write(self.tabs + "}\n")

    def visit_lit(self, lit: Literal):
        value = lit.value
        if isinstance(value, bool):
            self.buf.write("true" if value else "false")
        elif isinstance(value, int):
            self.buf.write(str(value))
        elif isinstance(value, str):
            self.buf.write(value)
        else:
            self.buf.write("0f")

    def visit_unary(self, unary: UnaryExpression):
        self.buf.write("(" + unary.op)
        if unary.op not in ("+", "-", "!"):
            self.buf.write(" ")
        self.visit(unary.value)
        self.buf.write(")")

    def visit_binary(self, binary: BinaryExpression):
        self.buf.write("(")
        self.visit(binary.lhs)
        self.buf.write(f" {binary.op} ")
        self.visit(binary.rhs)
        self.buf.write(")")

    def visit_conditional(self, cond: ConditionalExpression):
        self.buf.write("if ")
        self.visit(cond.cond)
        self.buf.write(" { ")
        self.visit(cond.then_expr)
        self.buf.write(" } else { ")
        self.visit(cond.else_expr)
        self.buf.write(" }")

    def visit_index(self, idx: IndexAccess):
        self.visit(idx.base)
        self.buf.write("[")
        self.visit(idx.index)
        self.buf.write("]")

    def visit_call(self, call: CallExpression):
        if call.name == "__array_lit__":
            self.buf.write("[")
            for idx, arg in enumerate(call.args):
                self.visit(arg)
                if idx + 1 != len(call.args):
                    self.buf.write(", ")
            self.buf.write("]")
            return

        if call.name == "__tuple__":
            self.buf.write("(")
            for idx, arg in enumerate(call.args):
                self.visit(arg)
                if idx + 1 != len(call.args):
                    self.buf.write(", ")
            self.buf.write(")")
            return

        self.buf.write(call.name + "(")
        for idx, arg in enumerate(call.args):
            self.visit(arg)
            if idx + 1 != len(call.args):
                self.buf.write(", ")
        self.buf.write(")")
