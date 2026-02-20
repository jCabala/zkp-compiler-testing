# -----------------------------
# zokrates/emitter.py
# -----------------------------
from __future__ import annotations
import io
from .nodes import *


class EmitVisitor:
    """
    ZoKrates code emitter for the local AST in zokrates/nodes.py.

    Key ZoKrates syntax points (0.8.x):
      - Mutable variables:     "<type> mut <name> = <expr>;"
        (NOT "mut <type> ..." and NOT "_mut")
      - For loops:             "for u32 i in a..b { ... }"
      - Multiple return:       "return (a, b);"
      - Arrays:                "<T>[N] x = [a, b, c];" is ok
                               (and also "[val; N]" exists but we don't generate it here)

    Robustness:
      - Never raises NotImplementedError: unknown nodes become a comment + "0f" (expr) or a comment line (stmt).
      - None expr becomes "0f /*NONE_EXPR*/"
      - None stmt is skipped.
    """

    def __init__(self):
        self.indent = 0
        self.buf = io.StringIO()

    def emit(self, node: ASTNode | None) -> str:
        self.indent = 0
        self.buf = io.StringIO()
        if node is None:
            self.writeln("// EMIT: AST_IS_NONE")
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

    # -------------------------
    # Core visiting
    # -------------------------
    def visit(self, node: ASTNode | None):
        if node is None:
            # expression-safe fallback
            self.buf.write("0f /*NONE_EXPR*/")
            return

        match node:
            # Top-level
            case Document():
                self.visit_document(node)
            case Function():
                self.visit_function(node)
            case Parameter():
                self.visit_parameter(node)

            # Statements
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

            # Expressions
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
                # Unknown node: never crash
                self.buf.write("0f /*UNSUPPORTED_EXPR*/")

    # -------------------------
    # Top level
    # -------------------------
    def visit_document(self, node: Document):
        self.visit(node.main)

    def visit_parameter(self, p: Parameter):
        if p.is_private:
            self.buf.write("private ")
        self.buf.write(f"{p.type_name} {p.name}")

    def visit_function(self, fn: Function):
        self.buf.write(f"def {fn.name}(")
        for i, p in enumerate(fn.params):
            self.visit_parameter(p)
            if i + 1 != len(fn.params):
                self.buf.write(", ")
        self.buf.write(")")
        if fn.return_type:
            self.buf.write(f" -> {fn.return_type}")
        self.buf.write(" {\n")

        self.indent += 4
        for s in fn.body:
            if s is None:
                continue
            self.visit(s)
            if not self.buf.getvalue().endswith("\n"):
                self.buf.write("\n")
        self.indent -= 4
        self.buf.write("}\n")

    # -------------------------
    # Statements
    # -------------------------
    def visit_let(self, s: LetStatement):
        # IMPORTANT: ZoKrates is "<type> mut <name> = <expr>;"
        # not "mut <type> ..." and not "_mut"
        self.buf.write(self.tabs + s.type_name)
        if s.is_mut:
            self.buf.write(" mut ")
        else:
            self.buf.write(" ")
        self.visit(s.name)
        self.buf.write(" = ")
        self.visit(s.expr)
        self.buf.write(";\n")

    def visit_assign(self, s: AssignStatement):
        self.buf.write(self.tabs)
        self.visit(s.lhs)
        self.buf.write(" = ")
        self.visit(s.rhs)
        self.buf.write(";\n")

    def visit_assert(self, s: AssertStatement):
        self.buf.write(self.tabs + "assert(")
        self.visit(s.cond)
        self.buf.write(");\n")

    def visit_expr_stmt(self, s: ExprStatement):
        self.buf.write(self.tabs)
        self.visit(s.expr)
        self.buf.write(";\n")

    def visit_return(self, s: ReturnStatement):
        if s.value is None:
            self.writeln("return;")
            return
        self.buf.write(self.tabs + "return ")
        self.visit(s.value)
        self.buf.write(";\n")

    def visit_for(self, s: ForLoop):
        self.buf.write(self.tabs + f"for u32 {s.index_name} in ")
        self.visit(s.start)
        self.buf.write("..")
        self.visit(s.end)
        self.buf.write(" {\n")

        self.indent += 4
        for st in s.body:
            if st is None:
                continue
            # If somehow a non-statement lands here, still don't crash
            if not isinstance(st, Statement):
                self.writeln("// EMIT: non-statement in for body skipped")
                continue
            self.visit(st)
            if not self.buf.getvalue().endswith("\n"):
                self.buf.write("\n")
        self.indent -= 4
        self.buf.write(self.tabs + "}\n")

    # -------------------------
    # Expressions
    # -------------------------
    def visit_lit(self, lit: Literal):
        v = lit.value
        if isinstance(v, bool):
            self.buf.write("true" if v else "false")
        elif isinstance(v, int):
            self.buf.write(str(v))
        elif isinstance(v, str):
            # RAW token (supports "0f", "1f", etc.)
            self.buf.write(v)
        else:
            self.buf.write("0f /*BAD_LITERAL*/")

    def visit_unary(self, u: UnaryExpression):
        self.buf.write("(" + u.op)
        if u.op not in ("+", "-", "!"):
            self.buf.write(" ")
        self.visit(u.value)
        self.buf.write(")")

    def visit_binary(self, b: BinaryExpression):
        self.buf.write("(")
        self.visit(b.lhs)
        self.buf.write(f" {b.op} ")
        self.visit(b.rhs)
        self.buf.write(")")

    def visit_conditional(self, c: ConditionalExpression):
        self.buf.write("if ")
        self.visit(c.cond)
        self.buf.write(" { ")
        self.visit(c.then_expr)
        self.buf.write(" } else { ")
        self.visit(c.else_expr)
        self.buf.write(" }")

    def visit_index(self, ia: IndexAccess):
        self.visit(ia.base)
        self.buf.write("[")
        self.visit(ia.index)
        self.buf.write("]")

    def visit_call(self, call: CallExpression):
        # Helpers used by the visitor
        if call.name == "__array_lit__":
            self.buf.write("[")
            for i, a in enumerate(call.args):
                self.visit(a)
                if i + 1 != len(call.args):
                    self.buf.write(", ")
            self.buf.write("]")
            return

        if call.name == "__tuple__":
            self.buf.write("(")
            for i, a in enumerate(call.args):
                self.visit(a)
                if i + 1 != len(call.args):
                    self.buf.write(", ")
            self.buf.write(")")
            return

        # Normal function call
        self.buf.write(call.name)
        self.buf.write("(")
        for i, a in enumerate(call.args):
            self.visit(a)
            if i + 1 != len(call.args):
                self.buf.write(", ")
        self.buf.write(")")
