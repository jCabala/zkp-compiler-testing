"""
IR to Mina/o1js AST transformation.

This module visits Circuzz IR nodes and transforms them into Mina/o1js AST nodes.
"""

from circuzz.ir import nodes as IRNodes
from circuzz.common.field import CurvePrime

from .nodes import *


class NameDispenser:
    """Generates unique variable names."""
    
    def __init__(self):
        self.__counter = 0
    
    def next(self, prefix: str = "v") -> Identifier:
        identifier = Identifier(f"{prefix}_{self.__counter}")
        self.__counter += 1
        return identifier


class IR2MinaVisitor:
    """
    Transforms Circuzz IR to Mina/o1js AST.
    
    Maps IR operations to o1js Field/Bool methods:
    - ADD: a.add(b)
    - SUB: a.sub(b)
    - MUL: a.mul(b)
    - DIV: a.div(b)
    - POW: uses Gadgets.Field.power() for field ** integer
    - EQU: a.equals(b)
    - NEQ: a.equals(b).not()
    - LTH: Gadgets.Field.lessThan(a, b)
    - GTH: Gadgets.Field.lessThan(b, a)
    - LEQ: Gadgets.Field.lessThanOrEqual(a, b)
    - GEQ: Gadgets.Field.lessThanOrEqual(b, a)
    - LAND: a.and(b)
    - LOR: a.or(b)
    - NOT: a.not()
    """
    
    def __init__(self, curve: CurvePrime, is_boolean_circuit: bool = False):
        self.__name_dispenser = NameDispenser()
        self.__is_boolean_circuit = is_boolean_circuit
    
    def transform(self, system: IRNodes.Circuit) -> Document:
        """Transform an IR circuit to Mina/o1js AST."""
        return self.visit_circuit(system)
    
    # =========================================================================
    # Expression Visitors
    # =========================================================================
    
    def visit_expression(self, node: IRNodes.IRNode) -> tuple[Expression, list[Statement]]:
        """Visit an expression and return the AST node + auxiliary statements."""
        match node:
            case IRNodes.Variable():
                return self.visit_variable(node)
            case IRNodes.Boolean():
                return self.visit_boolean(node)
            case IRNodes.Integer():
                return self.visit_integer(node)
            case IRNodes.UnaryExpression():
                return self.visit_unary_expression(node)
            case IRNodes.BinaryExpression():
                return self.visit_binary_expression(node)
            case IRNodes.TernaryExpression():
                return self.visit_ternary_expression(node)
            case _:
                raise NotImplementedError(f"Unknown expression type: {type(node).__name__}")
    
    def visit_variable(self, node: IRNodes.Variable) -> tuple[Expression, list[Statement]]:
        """Visit a variable reference."""
        return Identifier(node.name), []
    
    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        """Visit a boolean literal."""
        return BoolLiteral(node.value), []
    
    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        """Visit an integer literal."""
        return FieldLiteral(node.value), []
    
    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        """Visit a unary expression."""
        expr, statements = self.visit_expression(node.value)
        
        match node.op:
            case IRNodes.Operator.NOT:
                # Bool.not()
                result = MethodCall(expr, "not", [])
            case IRNodes.Operator.SUB:
                # Field negation: Field(0).sub(x) or x.neg()
                result = MethodCall(expr, "neg", [])
            case IRNodes.Operator.COMP:
                # Bitwise complement - not directly supported
                raise NotImplementedError("Bitwise complement (~) not supported in o1js")
            case _:
                raise NotImplementedError(f"Unary operator {node.op} not implemented")
        
        return result, statements
    
    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        """Visit a binary expression."""
        statements = []
        
        lhs, lhs_stmts = self.visit_expression(node.lhs)
        statements += lhs_stmts
        
        rhs, rhs_stmts = self.visit_expression(node.rhs)
        statements += rhs_stmts
        
        match node.op:
            # Arithmetic operations (Field methods)
            case IRNodes.Operator.ADD:
                result = MethodCall(lhs, "add", [rhs])
            case IRNodes.Operator.SUB:
                result = MethodCall(lhs, "sub", [rhs])
            case IRNodes.Operator.MUL:
                result = MethodCall(lhs, "mul", [rhs])
            case IRNodes.Operator.DIV:
                result = MethodCall(lhs, "div", [rhs])
            case IRNodes.Operator.POW:
                # For Field ** integer, use repeated squaring or power method
                # o1js doesn't have a direct pow, so we implement it
                result, pow_stmts = self._field_pow(lhs, rhs)
                statements += pow_stmts
            
            # Comparison operations
            case IRNodes.Operator.EQU:
                result = MethodCall(lhs, "equals", [rhs])
            case IRNodes.Operator.NEQ:
                eq_expr = MethodCall(lhs, "equals", [rhs])
                result = MethodCall(eq_expr, "not", [])
            case IRNodes.Operator.LTH:
                # a < b: use Field method lessThan
                result = MethodCall(lhs, "lessThan", [rhs])
            case IRNodes.Operator.GTH:
                # a > b: use Field method greaterThan
                result = MethodCall(lhs, "greaterThan", [rhs])
            case IRNodes.Operator.LEQ:
                # a <= b: use Field method lessThanOrEqual
                result = MethodCall(lhs, "lessThanOrEqual", [rhs])
            case IRNodes.Operator.GEQ:
                # a >= b: use Field method greaterThanOrEqual
                result = MethodCall(lhs, "greaterThanOrEqual", [rhs])
            
            # Logical operations (Bool methods)
            case IRNodes.Operator.LAND:
                result = MethodCall(lhs, "and", [rhs])
            case IRNodes.Operator.LOR:
                result = MethodCall(lhs, "or", [rhs])
            case IRNodes.Operator.LXOR:
                # a XOR b = (a OR b) AND NOT (a AND b)
                # Or simpler: a.equals(b).not()
                eq_expr = MethodCall(lhs, "equals", [rhs])
                result = MethodCall(eq_expr, "not", [])
            
            # Bitwise operations
            case IRNodes.Operator.AND | IRNodes.Operator.OR | IRNodes.Operator.XOR:
                raise NotImplementedError(f"Bitwise operator {node.op} not directly supported in o1js")
            
            case IRNodes.Operator.REM:
                raise NotImplementedError("Modulo (%) not supported in o1js field arithmetic")
            
            case _:
                raise NotImplementedError(f"Binary operator {node.op} not implemented")
        
        return result, statements
    
    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        """Visit a ternary/conditional expression using Provable.if()."""
        statements = []
        
        cond, cond_stmts = self.visit_expression(node.condition)
        statements += cond_stmts
        
        true_expr, true_stmts = self.visit_expression(node.if_expr)
        statements += true_stmts
        
        false_expr, false_stmts = self.visit_expression(node.else_expr)
        statements += false_stmts
        
        # Use Provable.if(condition, trueValue, falseValue)
        result = FunctionCall("Provable.if", [cond, true_expr, false_expr])
        
        return result, statements
    
    # =========================================================================
    # Statement Visitors
    # =========================================================================
    
    def visit_statement(self, node: IRNodes.IRNode) -> list[Statement]:
        """Visit a statement and return a list of AST statements."""
        match node:
            case IRNodes.Assertion():
                return self.visit_assertion(node)
            case IRNodes.Assignment():
                return self.visit_assignment(node)
            case IRNodes.Assume():
                return self.visit_assume(node)
            case _:
                raise NotImplementedError(f"Unknown statement type: {type(node).__name__}")
    
    def visit_assertion(self, node: IRNodes.Assertion) -> list[Statement]:
        """Visit an assertion statement."""
        statements = []
        
        value, value_stmts = self.visit_expression(node.value)
        statements += value_stmts
        
        # value.assertTrue(message)
        assert_call = MethodCall(value, "assertTrue", [])
        statements.append(ExpressionStatement(assert_call))
        
        return statements
    
    def visit_assignment(self, node: IRNodes.Assignment) -> list[Statement]:
        """Visit an assignment statement."""
        statements = []
        
        lhs, lhs_stmts = self.visit_expression(node.lhs)
        statements += lhs_stmts
        
        rhs, rhs_stmts = self.visit_expression(node.rhs)
        statements += rhs_stmts
        
        # Create const declaration
        assert isinstance(lhs, Identifier), "LHS of assignment must be an identifier"
        statements.append(ConstDeclaration(lhs.name, rhs))
        
        # Debug output
        statements += self._debug_expr(lhs)
        
        return statements
    
    def visit_assume(self, node: IRNodes.Assume) -> list[Statement]:
        """Visit an assume statement (treated as assertion)."""
        statements = []
        
        cond, cond_stmts = self.visit_expression(node.condition)
        statements += cond_stmts
        
        # Use assertTrue for assumptions
        assert_call = MethodCall(cond, "assertTrue", [])
        statements.append(ExpressionStatement(assert_call))
        
        return statements
    
    # =========================================================================
    # Circuit Visitor
    # =========================================================================
    
    def visit_circuit(self, node: IRNodes.Circuit) -> Document:
        """Visit a circuit and generate the complete o1js program."""
        # Imports needed for the program
        imports = [
            "import { Field, Bool, Provable, ZkProgram, Gadgets, Struct } from 'o1js';"
        ]
        
        # For boolean circuits, all inputs and outputs are Bool
        # For arithmetic circuits, all inputs and outputs are Field
        if self.__is_boolean_circuit:
            input_types = ["Bool"] * len(node.inputs)
            output_type = "Bool"
        else:
            input_types = ["Field"] * len(node.inputs)
            output_type = "Field"
        
        # Create method parameters from circuit inputs with correct types
        parameters = [
            MethodParameter(name, input_types[i])
            for i, name in enumerate(node.inputs)
        ]
        
        # Private input types
        private_input_types = input_types
        
        # Build method body
        body_statements: list[Statement] = []
        
        # Transform IR statements
        for stmt in node.statements:
            body_statements += self.visit_statement(stmt)
        
        # Create output list with names and types
        outputs = [OutputField(name, output_type) for name in node.outputs]
        
        # Return statement with all output names
        body_statements.append(ReturnStatement(node.outputs))
        
        # Create method definition
        method = MethodDefinition(
            name="compute",
            private_input_types=private_input_types,
            parameters=parameters,
            body=body_statements
        )
        
        # Create ZkProgram definition with output list
        program = ZkProgramDefinition(
            variable_name="circuit",
            program_name=node.name,
            outputs=outputs,
            methods=[method]
        )
        
        return Document(
            imports=imports,
            program=program,
            export_name="circuit"
        )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _field_pow(self, base: Expression, exponent: Expression) -> tuple[Expression, list[Statement]]:
        """Implement field exponentiation."""
        # For constant exponent, we can use repeated squaring inline
        # For now, assume exponent is a FieldLiteral
        if isinstance(exponent, FieldLiteral):
            exp_val = exponent.value
            if exp_val == 0:
                return FieldLiteral(1), []
            elif exp_val == 1:
                return base, []
            elif exp_val == 2:
                return MethodCall(base, "mul", [base]), []
            else:
                # Use repeated multiplication
                statements = []
                result_name = self.__name_dispenser.next("pow")
                
                # Start with base
                statements.append(ConstDeclaration(result_name.name, base))
                
                # Multiply exp_val - 1 more times
                current = result_name
                for i in range(exp_val - 1):
                    new_name = self.__name_dispenser.next("pow")
                    mul_expr = MethodCall(current, "mul", [base])
                    statements.append(ConstDeclaration(new_name.name, mul_expr))
                    current = new_name
                
                return current, statements
        else:
            # Dynamic exponent - would need more complex handling
            raise NotImplementedError("Dynamic exponents not yet supported in o1js backend")
    
    def _debug_expr(self, value: Expression) -> list[Statement]:
        """Generate debug print statements for an expression."""
        # Use Provable.log for circuit debugging
        log_call = FunctionCall("Provable.log", [value])
        return [ExpressionStatement(log_call)]
