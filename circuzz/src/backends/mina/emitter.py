"""
Mina/o1js AST code emission.

This module converts Mina/o1js AST nodes to TypeScript source code.
"""

import io
from .nodes import *


class EmitVisitor:
    """Emits Mina/o1js AST nodes as TypeScript code."""
    
    def __init__(self):
        self.indent = 0
        self.buffer = io.StringIO()
    
    @property
    def current_indent(self) -> str:
        return "  " * self.indent
    
    def emit(self, node: ASTNode) -> str:
        """Emit an AST node to source code string."""
        self.indent = 0
        self.buffer = io.StringIO()
        self.visit(node)
        return self.buffer.getvalue()
    
    def visit(self, node: ASTNode):
        """Dispatch to appropriate visit method based on node type."""
        match node:
            case Document():
                self.visit_document(node)
            case ZkProgramDefinition():
                self.visit_zkprogram_definition(node)
            case MethodDefinition():
                self.visit_method_definition(node)
            case ConstDeclaration():
                self.visit_const_declaration(node)
            case ExpressionStatement():
                self.visit_expression_statement(node)
            case ReturnStatement():
                self.visit_return_statement(node)
            case Identifier():
                self.visit_identifier(node)
            case FieldLiteral():
                self.visit_field_literal(node)
            case BoolLiteral():
                self.visit_bool_literal(node)
            case MethodCall():
                self.visit_method_call(node)
            case FunctionCall():
                self.visit_function_call(node)
            case _:
                raise NotImplementedError(f"Cannot emit node type: {type(node).__name__}")
    
    def _write(self, text: str):
        """Write text to the output buffer."""
        self.buffer.write(text)
    
    def _writeln(self, text: str = ""):
        """Write text with newline."""
        self.buffer.write(text + "\n")
    
    def _write_indent(self):
        """Write current indentation."""
        self._write(self.current_indent)
    
    # =========================================================================
    # Document and Program Structure
    # =========================================================================
    
    def visit_document(self, node: Document):
        """Emit complete document with imports and program."""
        # Imports
        for imp in node.imports:
            self._writeln(imp)
        self._writeln()
        
        # If multiple outputs, emit Struct definition first
        if len(node.program.outputs) > 1:
            self._emit_output_struct(node.program.outputs)
            self._writeln()
        
        # Program definition
        self.visit(node.program)
        self._writeln()
        
        # Export
        self._writeln(f"export {{ {node.export_name} }};")
    
    def _emit_output_struct(self, outputs: list):
        """Emit Struct definition for multiple outputs."""
        fields = ", ".join(f"{o.name}: {o.type_name}" for o in outputs)
        self._writeln(f"class CircuitOutput extends Struct({{ {fields} }}) {{}}")
    
    def visit_zkprogram_definition(self, node: ZkProgramDefinition):
        """Emit ZkProgram definition."""
        self._writeln(f"const {node.variable_name} = ZkProgram({{")
        self.indent += 1
        
        # Program name
        self._write_indent()
        self._writeln(f"name: '{node.program_name}',")
        
        # Public output type - handle 0, 1, or multiple outputs
        self._write_indent()
        if len(node.outputs) == 0:
            # No outputs - use undefined (ZkProgram allows this)
            self._writeln("publicOutput: undefined,")
        elif len(node.outputs) == 1:
            self._writeln(f"publicOutput: {node.outputs[0].type_name},")
        else:
            self._writeln("publicOutput: CircuitOutput,")
        self._writeln()
        
        # Methods
        self._write_indent()
        self._writeln("methods: {")
        self.indent += 1
        
        for i, method in enumerate(node.methods):
            self.visit_method_definition(method)
            if i < len(node.methods) - 1:
                self._writeln(",")
            else:
                self._writeln()
        
        self.indent -= 1
        self._write_indent()
        self._writeln("},")
        
        self.indent -= 1
        self._write("})")
    
    def visit_method_definition(self, node: MethodDefinition):
        """Emit method definition inside ZkProgram."""
        self._write_indent()
        self._writeln(f"{node.name}: {{")
        self.indent += 1
        
        # Private inputs
        self._write_indent()
        types_str = ", ".join(node.private_input_types)
        self._writeln(f"privateInputs: [{types_str}],")
        
        # Method signature
        self._write_indent()
        params_str = ", ".join(f"{p.name}: {p.type_name}" for p in node.parameters)
        self._writeln(f"async method({params_str}) {{")
        self.indent += 1
        
        # Method body
        for stmt in node.body:
            self._write_indent()
            self.visit(stmt)
            self._writeln()
        
        self.indent -= 1
        self._write_indent()
        self._writeln("},")
        
        self.indent -= 1
        self._write_indent()
        self._write("}")
    
    # =========================================================================
    # Statements
    # =========================================================================
    
    def visit_const_declaration(self, node: ConstDeclaration):
        """Emit const declaration."""
        self._write(f"const {node.name} = ")
        self.visit(node.value)
        self._write(";")
    
    def visit_expression_statement(self, node: ExpressionStatement):
        """Emit expression statement."""
        self.visit(node.expression)
        self._write(";")
    
    def visit_return_statement(self, node: ReturnStatement):
        """Emit return statement with public output(s)."""
        if len(node.output_names) == 0:
            # No outputs: return undefined (or empty object for ZkProgram)
            self._write("return;")
        elif len(node.output_names) == 1:
            # Single output: return { publicOutput: out0 };
            self._write(f"return {{ publicOutput: {node.output_names[0]} }};")
        else:
            # Multiple outputs: return { publicOutput: new CircuitOutput({ out0, out1, ... }) };
            fields = ", ".join(node.output_names)
            self._write(f"return {{ publicOutput: new CircuitOutput({{ {fields} }}) }};")
    
    # =========================================================================
    # Expressions
    # =========================================================================
    
    def visit_identifier(self, node: Identifier):
        """Emit identifier."""
        self._write(node.name)
    
    def visit_field_literal(self, node: FieldLiteral):
        """Emit Field literal."""
        # Use bigint notation for large numbers
        if node.value > 2**53 or node.value < -(2**53):
            self._write(f"Field({node.value}n)")
        else:
            self._write(f"Field({node.value})")
    
    def visit_bool_literal(self, node: BoolLiteral):
        """Emit Bool literal."""
        value_str = "true" if node.value else "false"
        self._write(f"Bool({value_str})")
    
    def visit_method_call(self, node: MethodCall):
        """Emit method call."""
        self.visit(node.receiver)
        self._write(f".{node.method}(")
        for i, arg in enumerate(node.arguments):
            if i > 0:
                self._write(", ")
            self.visit(arg)
        self._write(")")
    
    def visit_function_call(self, node: FunctionCall):
        """Emit function call."""
        self._write(f"{node.function}(")
        for i, arg in enumerate(node.arguments):
            if i > 0:
                self._write(", ")
            self.visit(arg)
        self._write(")")
