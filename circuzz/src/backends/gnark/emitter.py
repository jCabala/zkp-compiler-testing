import io

from .nodes import *

class EmitVisitor():

    def __init__(self, add_picus_annotations: bool = False):
        self.tabs = 0
        self.buffer = io.StringIO()
        self.add_picus_annotations = add_picus_annotations
        self.picus_input_names = []

    def emit(self, node: ASTNode) -> str:
        self.tabs = 0
        self.buffer = io.StringIO()
        self.visit(node)
        return self.buffer.getvalue()

    def emit_to_buffer(self, buffer: io.StringIO, node: ASTNode):
        self.tabs = 0
        _buffer = self.buffer
        self.buffer = buffer
        self.visit(node)
        self.buffer = _buffer # reset such that it cannot be misused

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

    def visit_circuit_struct_field(self, node: CircuitStructField):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"{node.name} frontend.Variable")
        # Annotate as public input if is_public, or as output if is_output
        if getattr(node, 'is_output', False):
            self.buffer.write(" `gnark:\",public\"` // Picus: output")
        elif node.is_public:
            self.buffer.write(" `gnark:\",public\"`")

    def visit_circuit_struct(self, node: CircuitStruct):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"type {node.name} struct {{\n")
        self.tabs += 1
        for field in node.fields:
            self.visit_circuit_struct_field(field)
            self.buffer.write("\n")

            if self.add_picus_annotations:
                if getattr(field, 'is_output', False):
                    if not hasattr(self, 'picus_output_names'):
                        self.picus_output_names = []
                    self.picus_output_names.append(field.name)
                else:
                    self.picus_input_names.append(field.name)

        self.tabs -= 1
        self.buffer.write("}")

    def visit_circuit_define_function(self, node: CircuitDefineFunction):
        self.buffer.write(f"func (circuit *{node.name}) Define(api frontend.API) error {{\n")
        self.tabs += 1

        if self.add_picus_annotations:
            self.annotate_picus_inputs()

        for stmt in node.statements:
            self.visit(stmt)
            self.buffer.write("\n")


        # Ensure all always-imported packages are referenced to avoid Go unused import errors.
        # This is necessary because the code generator may emit imports (e.g., math/big, bits, cmp) that are not always used,
        # and Go treats unused imports as compilation errors. These dummy references are safe even if the package is used elsewhere.
        self.buffer.write(f"{self.current_tabs}_ = big.NewInt\n")
        self.buffer.write(f"{self.current_tabs}_ = bits.ToBinary\n")
        self.buffer.write(f"{self.current_tabs}_ = cmp.IsLess\n")

        # finally return nil (no error)
        self.buffer.write(f"{self.current_tabs}return nil // no error\n")
        self.tabs -= 1
        self.buffer.write("}")

    def annotate_picus_inputs(self):
        for input_name in self.picus_input_names:
            self.buffer.write(self.current_tabs)
            self.buffer.write(f"picus_gnark.CircuitVarIn(circuit.{input_name})\n")
            self.buffer.write(self.current_tabs)
            self.buffer.write(f"picus_gnark.Label(circuit.{input_name}, \"{input_name}\")\n")
        if hasattr(self, 'picus_output_names'):
            for output_name in self.picus_output_names:
                self.buffer.write(self.current_tabs)
                self.buffer.write(f"picus_gnark.CircuitVarOut(circuit.{output_name})\n")
                self.buffer.write(self.current_tabs)
                self.buffer.write(f"picus_gnark.Label(circuit.{output_name}, \"{output_name}\")\n")
        self.buffer.write("\n")

    def add_picus_main_function(self, circuit_name: str):
        self.buffer.write("\n\nfunc main() {\n")
        self.tabs += 1
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"var circuit {circuit_name}\n")
        self.buffer.write(self.current_tabs)
        self.buffer.write("picus_gnark.CompilePicus(\"circuit\", &circuit, ecc.BN254.ScalarField())\n")
        self.tabs -= 1
        self.buffer.write("}")

    def visit_circuit_definition_collection(self, node: CircuitDefinitionCollection):
        if self.add_picus_annotations:
            self.buffer.write("package main\n\n")
            self.buffer.write("import (\n")
            self.buffer.write("\t\"math/big\"\n")
            self.buffer.write("\t\"github.com/Veridise/picus_gnark\"\n")
            self.buffer.write("\t\"github.com/consensys/gnark-crypto/ecc\"\n")
            self.buffer.write("\t\"github.com/consensys/gnark/frontend\"\n")
            self.buffer.write("\t\"github.com/consensys/gnark/std/math/bits\"\n")
            self.buffer.write("\t\"github.com/consensys/gnark/std/math/cmp\"\n")
            self.buffer.write(")\n\n")
        
        self.visit_circuit_struct(node.circuit_struct)
        self.buffer.write("\n\n")
        self.visit_circuit_define_function(node.circuit_define)

        if self.add_picus_annotations:
            self.add_picus_main_function(node.circuit_struct.name)

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
            if idx+1 != len(node.args): # if not the last
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
        else: # string
            assert node.is_str(), "unexpected literal"
            self.buffer.write(f"\"{node.value}\"")

    @property
    def current_tabs(self):
        return "\t" * self.tabs