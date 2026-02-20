from typing import cast
import io

from backends.circom.lib_path_resolver import LibPathMode, LibPathResolver

from .operators import *
from .nodes import *

@dataclass(frozen=True)
class EmitConfig():
    constrain_equality_assertions: bool
    constrain_sharp_inequality_assertions: bool

    lib_path_mode: LibPathMode = LibPathMode.DOCKER_GLOBAL

class EmitVisitor():

    def __init__(self, emit_config: EmitConfig):
        self.indent = 0
        self.buffer = io.StringIO()
        self.emit_config = emit_config
        self.comparator_out_idx = 0 # Index helpful for naming outputs needed for comparator circuits is we are constraining them

    def emit(self, node: ASTNode) -> str:
        self.indent = 0
        self.buffer = io.StringIO()
        self.visit(node)
        return self.buffer.getvalue()

    def visit(self, node: ASTNode, no_parentheses: bool = False):
        match node:
            case Identifier():
                self.visit_identifier(node)
            case Document():
                self.visit_document(node)
            case BasicBlock():
                self.visit_basic_block(node)
            case TemplateDefinition():
                self.visit_template_definition(node)
            case IncludeStatement():
                self.visit_include_statement(node)
            case VariableDefinition():
                self.visit_variable_definition(node)
            case SignalDefinition():
                self.visit_signal_definition(node)
            case ComponentDefinition():
                self.visit_component_definition(node)
            case AssignmentOrConstraint():
                self.visit_assignment_or_constraint(node)
            case IfStatement():
                self.visit_if_statement(node)
            case ForStatement():
                self.visit_for_statement(node)
            case WhileStatement():
                self.visit_while_statement(node)
            case AssertStatement():
                self.visit_assert_statement(node)
            case LogStatement():
                self.visit_log_statement(node)
            case ConditionalExpression():
                self.visit_conditional_expression(node)
            case BinaryExpression():
                self.visit_binary_expression(node,  no_parentheses=no_parentheses)
            case UnaryExpression():
                self.visit_unary_expression(node)
            case CallExpression():
                self.visit_call_expression(node)
            case IndexAccessExpression():
                self.visit_index_access_expression(node)
            case FieldAccessExpression():
                self.visit_field_access_expression(node)
            case IntegerLiteral():
                self.visit_integer_literal(node)
            case StringLiteral():
                self.visit_string_literal(node)
            case ListLiteral():
                self.visit_list_literal(node)
            case _:
                raise NotImplementedError()

    def visit_identifier(self, node: Identifier):
        self.buffer.write(node.name)

    def visit_document(self, node: Document):
        self.buffer.write("pragma circom " + node.version + ";\n")
        if node.custom:
            self.buffer.write("pragma custom_templates;\n")
        self.buffer.write("\n")

        # Add the necessary libraries
        # path_resolver = LibPathResolver(mode=self.emit_config.lib_path_mode)
        # if self.emit_config.constrain_sharp_inequality_assertions:
        #     comparators_path = path_resolver.get_comparators_path()
        #     self.buffer.write(f'include "{comparators_path}";\n\n')

        for stmt in node.statements:
            self.visit(stmt)
            self.buffer.write("\n")

        assert len(node.main.sizes) == 0, "only one main component allowed"
        assert not node.main.value is None, "requires definition value for main component"

        self.buffer.write(self.current_indent + "component ")
        self.visit(node.main.name)
        public_inp_len = len(node.public_inputs)
        if public_inp_len > 0:
            self.buffer.write("{public [")
            for idx, p_in in enumerate(node.public_inputs):
                self.visit(p_in)
                if not public_inp_len == (idx+1):
                    self.buffer.write(", ")
            self.buffer.write("]}")
        self.buffer.write(" = ")
        self.visit(node.main.value)
        self.buffer.write(";\n")

    def visit_basic_block(self, node: BasicBlock):
        self.buffer.write(self.current_indent + "{\n")
        self.indent += 4
        for stmt in node.statements:
            self.visit(stmt)
        self.indent -= 4
        self.buffer.write(self.current_indent + "}\n")

    def visit_template_definition(self, node: TemplateDefinition):
        self.buffer.write(self.current_indent + "template ")
        if node.custom:
            self.buffer.write("custom ")
        self.visit_identifier(node.name)
        self.buffer.write("(" + ", ".join([identifier.name for identifier in node.parameters]) + ") ")
        self.visit_basic_block(node.block)

    def visit_include_statement(self, node: IncludeStatement):
        path_resolver = LibPathResolver(mode=self.emit_config.lib_path_mode)
        self.buffer.write(self.current_indent + "include \"" + path_resolver.get_path_prefix() + node.dependency.value + "\"")
        #self.visit_string_literal(node.dependency)
        self.buffer.write(self.current_indent + ";\n")

    def visit_variable_definition(self, node: VariableDefinition):
        self.buffer.write(self.current_indent + "var ")
        self.visit(node.name)
        for size in node.sizes:
            self.buffer.write("[")
            self.visit(size)
            self.buffer.write("]")
        if not node.value is None:
            self.buffer.write(" = ")
            self.visit(node.value)
        self.buffer.write(";\n")

    def visit_signal_definition(self, node: SignalDefinition):
        self.buffer.write(self.current_indent + "signal ")
        if not node.kind == SignalKind.INTERMEDIATE:
            self.buffer.write(node.kind.value + " ")
        self.visit(node.name)
        for size in node.sizes:
            self.buffer.write("[")
            self.visit(size)
            self.buffer.write("]")
        if not node.value is None:
            self.buffer.write(" = ")
            self.visit(node.value)
        self.buffer.write(";\n")

    def visit_component_definition(self, node: ComponentDefinition):
        self.buffer.write(self.current_indent + "component ")
        self.visit(node.name)
        for size in node.sizes:
            self.buffer.write("[")
            self.visit(size)
            self.buffer.write("]")
        if not node.value is None:
            self.buffer.write(" = ")
            self.visit(node.value)
        self.buffer.write(";\n")

    def visit_assignment_or_constraint(self, node: AssignmentOrConstraint):
        self.buffer.write(self.current_indent)
        self.visit(node.name)
        self.buffer.write(" " + node.operator.value + " ")
        self.visit(node.value)
        self.buffer.write(";\n")

    def visit_if_statement(self, node: IfStatement):
        self.buffer.write(self.current_indent + "if(")
        self.visit(node.condition)
        self.buffer.write(") ")
        self.visit_basic_block(node.ifBlock)
        if not node.ifBlock is None:
            self.buffer.write(self.current_indent + "else ")
            self.visit_basic_block(cast(BasicBlock, node.elseBlock))

    def visit_for_statement(self, node: ForStatement):
        self.buffer.write(self.current_indent + "for(")
        cachedIndent = self.indent
        self.indent = 0
        self.visit(node.init)
        self.buffer.write("; ")
        self.visit(node.condition)
        self.buffer.write("; ")
        self.visit(node.step)
        self.buffer.write(")")
        self.indent = cachedIndent
        self.visit_basic_block(node.block)

    def visit_while_statement(self, node: WhileStatement):
        self.buffer.write(self.current_indent + "while(")
        self.visit(node.condition)
        self.buffer.write(")")
        self.visit_basic_block(node.block)

    def _is_equality_assertion(self, node: AssertStatement) -> bool:
        match node.condition:
            case BinaryExpression():
                return node.condition.operator == Operator.EQU
            case _:
                return False
            
    def _is_sharp_inequality_assertion(self, node: AssertStatement) -> bool:
        match node.condition:
            case BinaryExpression():
                return node.condition.operator in [Operator.LTH, Operator.GTH]
            case _:
                return False
            
    def visit_assert_statement(self, node: AssertStatement):
        if node.unwrapped:
            self.visit(node.condition, no_parentheses=True)
            self.buffer.write(";\n")
            return

        if self.emit_config.constrain_equality_assertions and self._is_equality_assertion(node):
            self.buffer.write(self.current_indent)
            self.visit_equality_assertion_as_constraint(node)
            return
        
        if self.emit_config.constrain_sharp_inequality_assertions and self._is_sharp_inequality_assertion(node):
            # Add new line if last line in buffer is not empty
            if not self.buffer.getvalue().endswith("\n\n"):
                self.buffer.write("\n")
            
            component_name = f"ineq_{self.comparator_out_idx}"
            comparator = "LessThan" if node.condition.operator == Operator.LTH else "GreaterThan"

            self.buffer.write(self.current_indent + f"component {component_name} = {comparator}(252);\n")
            self.buffer.write(self.current_indent + f"{component_name}.in[0] <== ")
            self.visit(node.condition.lhs)
            self.buffer.write(";\n")
            self.buffer.write(self.current_indent + f"{component_name}.in[1] <== ")
            self.visit(node.condition.rhs)
            self.buffer.write(";\n")
            self.buffer.write(self.current_indent + f"{component_name}.out === 1;\n")

            self.buffer.write("\n")
            self.comparator_out_idx += 1
            return
            
        self.buffer.write(self.current_indent + "assert(")
        self.visit(node.condition)
        self.buffer.write(");\n")
            
    def visit_equality_assertion_as_constraint(self, node: AssertStatement):
        match node.condition:
            case BinaryExpression():
                self.visit(node.condition.lhs)
                self.buffer.write(" === ")
                self.visit(node.condition.rhs)
                self.buffer.write(";\n")
            case _:
                raise NotImplementedError("Expected BinaryExpression for equality assertion")

    def visit_log_statement(self, node: LogStatement):
        self.buffer.write(self.current_indent + "log(")
        for (i,e) in enumerate(node.arguments):
            self.visit(e)
            if i + 1 < len(node.arguments):
                self.buffer.write(", ")
        self.buffer.write(");\n")

    def visit_conditional_expression(self, node: ConditionalExpression):
        self.buffer.write("(")
        self.visit(node.condition)
        self.buffer.write(" ? ")
        self.visit(node.trueVal)
        self.buffer.write(" : ")
        self.visit(node.falseVal)
        self.buffer.write(")")

    def visit_binary_expression(self, node: BinaryExpression, no_parentheses: bool = False):
        if not no_parentheses:
            self.buffer.write("(")
        self.visit(node.lhs)
        self.buffer.write(" " + node.operator.value + " ")
        self.visit(node.rhs)
        if not no_parentheses:
            self.buffer.write(")")

    def visit_unary_expression(self, node: UnaryExpression):
        self.buffer.write("(")
        self.buffer.write(node.operator.value + " ")
        self.visit(node.value)
        self.buffer.write(")")

    def visit_call_expression(self, node: CallExpression):
        self.visit(node.reference)
        self.buffer.write("(")
        size = len(node.arguments)
        for idx, arg in enumerate(node.arguments):
            self.visit(arg)
            if not size == (idx + 1): # if not last
                self.buffer.write(", ")
        self.buffer.write(")")

    def visit_index_access_expression(self, node: IndexAccessExpression):
        self.visit(node.reference)
        self.buffer.write("[")
        self.visit(node.index)
        self.buffer.write("]")

    def visit_field_access_expression(self, node: FieldAccessExpression):
        self.visit(node.reference)
        self.buffer.write(".")
        self.visit(node.field)

    def visit_integer_literal(self, node: IntegerLiteral):
        self.buffer.write(str(node.value))

    def visit_string_literal(self, node: StringLiteral):
        self.buffer.write("\"" + node.value + "\"")

    def visit_list_literal(self, node: ListLiteral):
        self.buffer.write("[")
        size = len(node.value)
        for idx, v in enumerate(node.value):
            self.visit(v)
            if not size == (idx+1):
                self.buffer.write(", ")
        self.buffer.write("]")

    @property
    def current_indent(self):
        return " " * self.indent
