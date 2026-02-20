"""
Mina/o1js AST node definitions.

This module defines classes representing Mina/o1js code constructs
that can be emitted as TypeScript code.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    
    def copy(self) -> 'ASTNode':
        raise NotImplementedError()


# =============================================================================
# Expressions
# =============================================================================

@dataclass
class Expression(ASTNode):
    """Base class for expressions."""
    
    def copy(self) -> 'Expression':
        raise NotImplementedError()


@dataclass
class Identifier(Expression):
    """Variable or reference identifier."""
    name: str
    
    def copy(self) -> 'Identifier':
        return Identifier(self.name)


@dataclass
class FieldLiteral(Expression):
    """Field element literal: Field(123)"""
    value: int
    
    def copy(self) -> 'FieldLiteral':
        return FieldLiteral(self.value)


@dataclass
class BoolLiteral(Expression):
    """Boolean literal: Bool(true)"""
    value: bool
    
    def copy(self) -> 'BoolLiteral':
        return BoolLiteral(self.value)


@dataclass
class MethodCall(Expression):
    """
    Method call on an object: obj.method(args)
    Examples: x.add(y), x.mul(y), x.assertEquals(y)
    """
    receiver: Expression
    method: str
    arguments: list[Expression] = field(default_factory=list)
    
    def copy(self) -> 'MethodCall':
        return MethodCall(
            self.receiver.copy(),
            self.method,
            [arg.copy() for arg in self.arguments]
        )


@dataclass
class FunctionCall(Expression):
    """
    Function call: func(args)
    Examples: Provable.if(cond, Field, a, b), Gadgets.xor(a, b, 254)
    """
    function: str
    arguments: list[Expression] = field(default_factory=list)
    
    def copy(self) -> 'FunctionCall':
        return FunctionCall(
            self.function,
            [arg.copy() for arg in self.arguments]
        )


# =============================================================================
# Statements
# Statements
# =============================================================================

@dataclass
class Statement(ASTNode):
    """Base class for statements."""
    
    def copy(self) -> 'Statement':
        raise NotImplementedError()


@dataclass
class ConstDeclaration(Statement):
    """
    Const declaration: const name = value;
    """
    name: str
    value: Expression
    type_annotation: Optional[str] = None
    
    def copy(self) -> 'ConstDeclaration':
        return ConstDeclaration(
            self.name,
            self.value.copy(),
            self.type_annotation
        )


@dataclass
class ExpressionStatement(Statement):
    """
    Expression as statement: expr;
    Used for assertions like x.assertEquals(y);
    """
    expression: Expression
    
    def copy(self) -> 'ExpressionStatement':
        return ExpressionStatement(self.expression.copy())


@dataclass
class ReturnStatement(Statement):
    """
    Return statement for ZkProgram outputs.
    - Single output: return out0;
    - Multiple outputs: return new CircuitOutput({ out0, out1, ... });
    """
    output_names: list[str]  # List of output variable names
    
    def copy(self) -> 'ReturnStatement':
        return ReturnStatement(self.output_names.copy())


# =============================================================================
# Program Structure
# =============================================================================

@dataclass
class MethodParameter:
    """Method parameter: name: Type"""
    name: str
    type_name: str = "Field"
    
    def copy(self) -> 'MethodParameter':
        return MethodParameter(self.name, self.type_name)


@dataclass
class MethodDefinition(ASTNode):
    """
    ZkProgram method definition:
    methodName: {
      privateInputs: [Field, Field, ...],
      async method(param1: Field, ...) {
        // body
      }
    }
    """
    name: str
    parameters: list[MethodParameter]
    body: list[Statement]
    private_input_types: list[str] = field(default_factory=list)
    
    def copy(self) -> 'MethodDefinition':
        return MethodDefinition(
            self.name,
            [p.copy() for p in self.parameters],
            [s.copy() for s in self.body],
            self.private_input_types.copy()
        )


@dataclass
class OutputField:
    """Single output field with name and type."""
    name: str
    type_name: str = "Field"


@dataclass
class ZkProgramDefinition(ASTNode):
    """
    ZkProgram definition:
    const ProgramName = ZkProgram({
      name: 'program-name',
      publicOutput: Field,  // or a Struct for multiple outputs
      methods: { ... }
    });
    """
    variable_name: str
    program_name: str
    outputs: list[OutputField]  # List of outputs (name, type)
    methods: list[MethodDefinition]
    
    def copy(self) -> 'ZkProgramDefinition':
        return ZkProgramDefinition(
            self.variable_name,
            self.program_name,
            [OutputField(o.name, o.type_name) for o in self.outputs],
            [m.copy() for m in self.methods]
        )


@dataclass
class Document(ASTNode):
    """
    Complete Mina/o1js document with imports and program definition.
    """
    imports: list[str]
    program: ZkProgramDefinition
    export_name: str
    
    def copy(self) -> 'Document':
        return Document(
            self.imports.copy(),
            self.program.copy(),
            self.export_name
        )