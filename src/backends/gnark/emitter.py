import io
from pathlib import Path

from .nodes import *


class EmitVisitor():

    def __init__(self, main_template_path: str = "./main_template.go"):
        self.tabs = 0
        self.buffer = io.StringIO()
        here = Path(__file__).resolve().parent
        self.main_template_path = here / main_template_path

    def emit(self, node: ASTNode) -> str:
        self.tabs = 0
        self.buffer = io.StringIO()

        # --- Go file prolog (package + imports) ---
        self.buffer.write("package main\n\n")
        self.buffer.write("import (\n")
        self.buffer.write("\t\"os\"\n")
        self.buffer.write("\t\"strings\"\n")
        self.buffer.write("\t\"fmt\"\n")
        self.buffer.write("\t\"encoding/json\"\n")
        self.buffer.write("\t\"github.com/consensys/gnark-crypto/ecc\"\n")
        self.buffer.write("\t\"github.com/consensys/gnark/frontend\"\n")
        self.buffer.write("\t\"github.com/consensys/gnark/frontend/cs/r1cs\"\n")
        self.buffer.write("\t\"github.com/consensys/gnark/constraint\"\n")
        self.buffer.write(")\n\n")

        # --- emit the circuit (type + Define) ---
        self.visit(node)

        # --- append main() from template, JSON-only ---
        if isinstance(node, CircuitDefinitionCollection):
            self._append_main_template(node.name)

        return self.buffer.getvalue()

    def _append_main_template(self, circuit_name: str):
        template_path = Path(self.main_template_path)
        template = template_path.read_text(encoding="utf-8")
        template = template.replace("__CIRCUIT_NAME__", circuit_name)
        self.buffer.write("\n\n")
        self.buffer.write(template)

    # ---------------- visitor dispatch ----------------

    def visit(self, node: ASTNode):
        match node:
            case CircuitStructField():
                self.visit_circuit_struct_field(node)
            case CircuitStruct():
                self.visit_circuit_struct(node)
            case CircuitDefineFunction():
                self.visit_circuit_define_function(node)
            case CircuitDefinitionCollection():
                self.visit_circuit_definition_collection(node)
            case CallStatement():
                self.visit_call_statement(node)
            case AssignStatement():
                self.visit_assign_statement(node)
            case ForLoop():
                self.visit_for_loop(node)
            case Identifier():
                self.visit_identifier(node)
            case FieldAccessExpression():
                self.visit_field_access_expression(node)
            case CallExpression():
                self.visit_call_expression(node)
            case IndexAccessExpression():
                self.visit_index_access_expression(node)
            case Literal():
                self.visit_literal(node)
            case _:
                raise NotImplementedError(f"unsupported node type '{node.__class__}'")

    # ---------------- Circuit structure ----------------

    def visit_circuit_struct_field(self, node: CircuitStructField):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"{node.name} frontend.Variable")
        if node.is_public:
            self.buffer.write(" `gnark:\",public\"`")

    def visit_circuit_struct(self, node: CircuitStruct):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"type {node.name} struct {{\n")
        self.tabs += 1
        for field in node.fields:
            self.visit_circuit_struct_field(field)
            self.buffer.write("\n")
        self.tabs -= 1
        self.buffer.write("}")

    def visit_circuit_define_function(self, node: CircuitDefineFunction):
        self.buffer.write(f"func (circuit *{node.name}) Define(api frontend.API) error {{\n")
        self.tabs += 1
        for stmt in node.statements:
            self.visit(stmt)
            self.buffer.write("\n")
        self.buffer.write(f"{self.current_tabs}return nil // no error\n")
        self.tabs -= 1
        self.buffer.write("}")

    def visit_circuit_definition_collection(self, node: CircuitDefinitionCollection):
        self.visit_circuit_struct(node.circuit_struct)
        self.buffer.write("\n\n")
        self.visit_circuit_define_function(node.circuit_define)

    # ---------------- Statements ----------------

    def visit_call_statement(self, node: CallStatement):
        self.buffer.write(self.current_tabs)
        self.visit_call_expression(node.expr)

    def visit_assign_statement(self, node: AssignStatement):
        self.buffer.write(self.current_tabs)
        self.visit(node.lhs)
        self.buffer.write(" := " if node.is_definition else " = ")
        self.visit(node.rhs)

    def visit_for_loop(self, node: ForLoop):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"for {node.index_var} := ")
        self.visit(node.start)
        self.buffer.write(f"; {node.index_var} < ")
        self.visit(node.end)
        self.buffer.write(f"; {node.index_var}++ {{\n")
        self.tabs += 1
        for e in node.body:
            self.visit(e)
            self.buffer.write("\n")
        self.tabs -= 1
        self.buffer.write(self.current_tabs)
        self.buffer.write("}")

    # ---------------- Expressions ----------------

    def visit_identifier(self, node: Identifier):
        self.buffer.write(node.name)

    def visit_field_access_expression(self, node: FieldAccessExpression):
        self.visit(node.expr)
        self.buffer.write(".")
        self.buffer.write(node.field)

    def visit_call_expression(self, node: CallExpression):
        self.visit(node.expr)
        self.buffer.write("(")
        for idx, arg in enumerate(node.args):
            self.visit(arg)
            if idx + 1 != len(node.args):
                self.buffer.write(", ")
        self.buffer.write(")")

    def visit_index_access_expression(self, node: IndexAccessExpression):
        self.visit(node.expr)
        self.buffer.write("[")
        self.visit(node.index)
        self.buffer.write("]")

    def visit_literal(self, node: Literal):
        if node.is_bool():
            self.buffer.write("true" if node.value else "false")
        elif node.is_int():
            self.buffer.write(str(node.value))
        else:
            assert node.is_str(), "unexpected literal"
            self.buffer.write(f"\"{node.value}\"")

    @property
    def current_tabs(self):
        return "\t" * self.tabs
