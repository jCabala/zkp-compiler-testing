# =========================
# PATCH: Visitor upgrades
# =========================
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from random import Random
from typing import cast

from circuzz.ir import nodes as IRNodes
from .nodes import *
from .operators import *

# --------------------------------------------------------------------
# (keep your NameDispenser / ImportDependency / ImportDependencyManager)
# --------------------------------------------------------------------

class NameDispenser():
    def __init__(self):
        self.__unique_var_counter = 0
    def next(self, prefix: str = "") -> Identifier:
        identifier = Identifier(f"{prefix}_{self.__unique_var_counter}")
        self.__unique_var_counter += 1
        return identifier

class ImportDependency(Enum):
    COMPARATORS = "comparators.circom"
    GATES = "gates.circom"
    MUX = "mux1.circom"

@dataclass
class ImportDependencyManager():
    dependencies : set[ImportDependency] = field(default_factory=set)

def bernoulli(p: float, rng: Random) -> bool:
    return True #rng.random() < p


# ================================================================
# Base Visitor (unchanged except: you can optionally use the new
# IR2CircomVisitorConstrainAssertions below instead of this base)
# ================================================================
class IR2CircomVisitor():
    __name_dispenser              : NameDispenser
    __dependency_manager          : ImportDependencyManager
    __constraint_assignment_probability : float
    __rng : Random

    def __init__(self, constraint_assignment_probability: float, rng: Random):
        self.__name_dispenser = NameDispenser()
        self.__dependency_manager = ImportDependencyManager()

        self.__assert_divisor_non_zero_assumption = True
        self.__constraint_assignment_probability = constraint_assignment_probability
        self.__rng = rng

    def transform(self, system: IRNodes.Circuit) -> Document:
        return self.visit_circuit(system)

    def visit_operator(self, ir_op: IRNodes.Operator) -> Operator:
        mapping = \
            { IRNodes.Operator.MUL : Operator.MUL
            , IRNodes.Operator.SUB : Operator.SUB
            , IRNodes.Operator.ADD : Operator.ADD
            , IRNodes.Operator.POW : Operator.POW
            , IRNodes.Operator.EQU : Operator.EQU
            , IRNodes.Operator.LTH : Operator.LTH
            , IRNodes.Operator.LEQ : Operator.LEQ
            , IRNodes.Operator.GTH : Operator.GTH
            , IRNodes.Operator.GEQ : Operator.GEQ
            , IRNodes.Operator.NEQ : Operator.NEQ
            , IRNodes.Operator.LAND : Operator.LAND
            , IRNodes.Operator.LOR : Operator.LOR
            , IRNodes.Operator.NOT : Operator.NOT
            , IRNodes.Operator.DIV : Operator.DIV
            , IRNodes.Operator.REM : Operator.REM
            , IRNodes.Operator.COMP : Operator.COMP
            , IRNodes.Operator.AND : Operator.AND
            , IRNodes.Operator.OR : Operator.OR
            , IRNodes.Operator.XOR : Operator.XOR
            , IRNodes.Operator.LXOR : Operator.XOR
            }
        ast_op = mapping.get(ir_op, None)
        if ast_op == None:
            raise NotImplementedError(f"unimplemented IR operator {ir_op.value}")
        return ast_op

    def visit_expression(self, node: IRNodes.IRNode) -> tuple[Expression, list[Statement]]:
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
                raise NotImplementedError()

    def visit_statement(self, node: IRNodes.IRNode) -> tuple[Statement, list[Statement]]:
        match node:
            case IRNodes.Assertion():
                return self.visit_assertion(node)
            case IRNodes.Assignment():
                return self.visit_assignment(node)
            case IRNodes.Assume():
                return self.visit_assume(node)
            case _:
                raise NotImplementedError()

    def visit_variable(self, node: IRNodes.Variable) -> tuple[Expression, list[Statement]]:
        return Identifier(node.name), []

    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        return IntegerLiteral(1 if node.value else 0), []

    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        return IntegerLiteral(node.value), []

    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        expression, statements = self.visit_expression(node.value)
        op = self.visit_operator(node.op)
        return UnaryExpression(op, expression), statements

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        statements = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail
        op = self.visit_operator(node.op)
        return BinaryExpression(op, lhs, rhs), statements

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        statements = []
        cond, cond_tail = self.visit_expression(node.condition)
        statements += cond_tail
        if_expr, if_expr_tail = self.visit_expression(node.if_expr)
        statements += if_expr_tail
        else_expr, else_expr_tail = self.visit_expression(node.else_expr)
        statements += else_expr_tail
        expression = ConditionalExpression(cond, if_expr, else_expr)

        # always move ternary to a tmp variable
        variable_name = self.__name_dispenser.next("var")
        statements.append(VariableDefinition(variable_name, [], expression))
        return variable_name.copy(), statements

    # default: boolean-only runtime assert (unchanged)
    def visit_assertion(self, node: IRNodes.Assertion) -> tuple[Statement, list[Statement]]:
        expression, statements = self.visit_expression(node.value)
        return AssertStatement(expression), statements

    def visit_assignment(self, node: IRNodes.Assignment) -> tuple[Statement, list[Statement]]:
        statements: list[Statement] = []
        if bernoulli(self.__constraint_assignment_probability, self.__rng):
            assignment, stmts = IR2ConstraintCircomVisitor(
                self.__name_dispenser,
                self.__dependency_manager,
                comparison_nbits=252,
                assertion_mode=False,
            ).visit_assignment(node)
            statements += stmts
            return assignment, statements

        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail
        assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, lhs, rhs)
        return assignment, statements

    def visit_assume(self, node: IRNodes.Assume) -> tuple[Statement, list[Statement]]:
        condition, stmts = self.visit_expression(node.condition)
        if self.__assert_divisor_non_zero_assumption:
            return AssertStatement(condition, f"{node.identifier} violation detected!"), stmts
        return LogStatement([StringLiteral("<!> assume: "), condition]), stmts

    def visit_circuit(self, node: IRNodes.Circuit) -> Document:
        circuit_template_name = Identifier("main_template")
        circuit_statements: list[Statement] = []
        circuit_statements += [SignalDefinition(Identifier(v), SignalKind.INPUT) for v in node.inputs]
        circuit_statements += [SignalDefinition(Identifier(v), SignalKind.OUTPUT) for v in node.outputs]

        # # constrain boolean inputs and outputs with x * (1 - x) === 0
        # all_signals = node.inputs + node.outputs
        # for var in all_signals:
        #     if var.variable_type == IRNodes.VariableType.BOOLEAN:
        #         circuit_statements.append(
        #             self._assert_zero(
        #                 BinaryExpression(
        #                     Operator.MUL,
        #                     Identifier(var.name),
        #                     BinaryExpression(
        #                         Operator.SUB,
        #                         IntegerLiteral(1),
        #                         Identifier(var.name)
        #                     )
        #                 )
        #             )
        #         )

        for statement in node.statements:
            stmt, tail = self.visit_statement(statement)
            circuit_statements += tail
            circuit_statements.append(stmt)

        circuit_statements += self._log_statements_for_signals(node.outputs)

        circuit_block = BasicBlock(circuit_statements)
        circuit_template = TemplateDefinition(circuit_template_name, [], circuit_block)

        main_component_name = Identifier("main")
        main_template_ref = Identifier("main_template")
        main_template_inst = CallExpression(main_template_ref)
        main_component = ComponentDefinition(main_component_name,  [], main_template_inst)

        document_definitions: list[Statement] = []
        for dependency in self.__dependency_manager.dependencies:
            document_definitions.append(IncludeStatement(StringLiteral(dependency.value)))

        document_definitions.append(circuit_template)
        return Document(document_definitions, main_component)

    def _assert_not_zero(self, value: Expression, msg: str | None = None) -> Statement:
        zero_lit = IntegerLiteral(0)
        is_not_zero_expr = BinaryExpression(Operator.NEQ, value.copy(), zero_lit)
        return AssertStatement(is_not_zero_expr, msg)

    def _assert_zero(self, value: Expression, msg: str | None = None) -> Statement:
        zero_lit = IntegerLiteral(0)
        is_zero_expr = BinaryExpression(Operator.EQU_CONSTRAINT, value.copy(), zero_lit)
        return AssertStatement(is_zero_expr, msg, unwrapped=True)

    def _log_statements_for_signals(self, names: list[str]) -> list[Statement]:
        statements: list[Statement] = []
        for name in names:
            identifier = Identifier(name)
            statements.append(LogStatement([StringLiteral(f"<@> {name} = "), identifier]))
        return statements


# ======================================================================
# Constraint Visitor: NOW supports splitting + full comparator constraints
# + assertion_mode to forbid unconstrained ops inside assertions
# ======================================================================
class IR2ConstraintCircomVisitor(IR2CircomVisitor):
    __name_dispenser     : NameDispenser
    __dependency_manager : ImportDependencyManager
    __comparison_nbits   : int
    __assertion_mode     : bool

    def __init__(
        self,
        name_dispenser: NameDispenser,
        import_manager: ImportDependencyManager,
        comparison_nbits: int = 252,
        assertion_mode: bool = False,
    ):
        self.__name_dispenser = name_dispenser
        self.__dependency_manager = import_manager
        self.__comparison_nbits = comparison_nbits
        self.__assertion_mode = assertion_mode

    # -------------------
    # Expression lowering
    # -------------------
    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        match node.op:
            case IRNodes.Operator.NOT:
                value, statements = self.visit_expression(node.value)
                not_expr, not_stmts = self._constrained_not(value)
                return not_expr, statements + not_stmts

            case IRNodes.Operator.COMP:
                # In assertion mode, forbid unconstrained ops
                if self.__assertion_mode:
                    raise NotImplementedError("COMP is not constrained; forbidden inside assertions.")
                value, statements = self.visit_expression(node.value)
                comp_expr = UnaryExpression(Operator.COMP, value)
                signal = self._next_intermediate_signal()
                statements.append(signal)
                statements.append(
                    AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, signal.name.copy(), comp_expr)
                )
                return signal.name.copy(), statements

            case IRNodes.Operator.SUB:
                return super().visit_unary_expression(node)

            case _:
                raise NotImplementedError(f"unimplemented simplification for unary operator {node.op}")

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        lhs, lhs_tail = self.visit_expression(node.lhs)
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements: list[Statement] = []
        statements += lhs_tail
        statements += rhs_tail

        match node.op:
            case IRNodes.Operator.POW:
                expr, tail = self.simplify_pow_expression(node, lhs, rhs)
            case IRNodes.Operator.MUL:
                expr, tail = self.simplify_mul_expression(node, lhs, rhs)
            case IRNodes.Operator.ADD | IRNodes.Operator.SUB:
                expr, tail = self.simplify_add_or_sub_expression(node, lhs, rhs)
            case IRNodes.Operator.EQU | IRNodes.Operator.LTH | IRNodes.Operator.LEQ | IRNodes.Operator.GTH | IRNodes.Operator.GEQ | IRNodes.Operator.NEQ:
                expr, tail = self.simplify_relation_expression(node, lhs, rhs)
            case IRNodes.Operator.LAND | IRNodes.Operator.LOR | IRNodes.Operator.LXOR:
                expr, tail = self.simplify_binary_boolean_logic_expression(node, lhs, rhs)
            case IRNodes.Operator.DIV:
                expr, tail = self.simplify_div_expression(node, lhs, rhs)
            case IRNodes.Operator.REM:
                expr, tail = self.simplify_rem_expression(node, lhs, rhs)
            case IRNodes.Operator.AND | IRNodes.Operator.OR | IRNodes.Operator.XOR:
                expr, tail = self.simplify_bitwise_expression(node, lhs, rhs)
            case _:
                raise NotImplementedError(f"binary operator {node.op.value}")

        return expr, statements + tail

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        cond, cond_tail = self.visit_expression(node.condition)
        if_expr, if_tail = self.visit_expression(node.if_expr)
        else_expr, else_tail = self.visit_expression(node.else_expr)

        expr, tail = self.simplify_ternary_expression(node, cond, if_expr, else_expr)
        return expr, cond_tail + if_tail + else_tail + tail

    def visit_assignment(self, node: IRNodes.Assignment) -> tuple[Statement, list[Statement]]:
        statements: list[Statement] = []
        signal_reference, reference_tail = self.visit_expression(node.lhs)
        statements += reference_tail
        constraint_expression, tail_stmts = self.visit_expression(node.rhs)
        statements += tail_stmts
        stmt = AssignmentOrConstraint(
            Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT,
            signal_reference,
            constraint_expression
        )
        return stmt, statements

    # -------------------
    # Splitting utilities
    # -------------------
    def _force_signal(self, expr: Expression, statements: list[Statement]) -> Expression:
        """
        Ensure comparator inputs (and other places you want to be strict)
        are fed as a simple signal identifier.
        """
        if isinstance(expr, Identifier):
            return expr
        sig = self._next_intermediate_signal()
        statements.append(sig)
        statements.append(
            AssignmentOrConstraint(
                Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT,
                sig.name.copy(),
                expr.copy(),
            )
        )
        return sig.name.copy()

    # -------------------
    # Algebra simplifiers
    # -------------------
    def simplify_pow_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        assert node.op == IRNodes.Operator.POW
        statements: list[Statement] = []
        constraint_op = Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT

        if self._is_constant(lhs):
            return BinaryExpression(Operator.POW, lhs, rhs), statements

        assert isinstance(rhs, IntegerLiteral)
        exponent = cast(IntegerLiteral, rhs).value
        assert exponent >= 2

        s0 = self._next_intermediate_signal()
        statements.append(s0)
        statements.append(AssignmentOrConstraint(constraint_op, s0.name.copy(), lhs.copy()))

        ref = s0.name.copy()
        for _ in range(exponent - 1):
            sn = self._next_intermediate_signal()
            statements.append(sn)
            statements.append(
                AssignmentOrConstraint(
                    constraint_op,
                    sn.name.copy(),
                    BinaryExpression(Operator.MUL, ref, s0.name.copy())
                )
            )
            ref = sn.name.copy()
        return ref, statements

    def simplify_mul_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        assert node.op == IRNodes.Operator.MUL
        statements: list[Statement] = []
        constraint_op = Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT

        if self._is_at_least_quadratic(lhs) and self._contains_variable(rhs):
            inter = self._next_intermediate_signal()
            statements.append(inter)
            statements.append(AssignmentOrConstraint(constraint_op, inter.name.copy(), lhs))
            lhs = inter.name.copy()

        if self._contains_variable(lhs) and self._is_at_least_quadratic(rhs):
            inter = self._next_intermediate_signal()
            statements.append(inter)
            statements.append(AssignmentOrConstraint(constraint_op, inter.name.copy(), rhs))
            rhs = inter.name.copy()

        return BinaryExpression(Operator.MUL, lhs, rhs), statements

    def simplify_add_or_sub_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        assert node.op in [IRNodes.Operator.ADD, IRNodes.Operator.SUB]
        statements: list[Statement] = []
        constraint_op = Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT

        if self._is_at_least_quadratic(lhs) and self._is_at_least_quadratic(rhs):
            inter = self._next_intermediate_signal()
            statements.append(inter)
            statements.append(AssignmentOrConstraint(constraint_op, inter.name.copy(), lhs))
            lhs = inter.name.copy()

        if node.op == IRNodes.Operator.ADD:
            return BinaryExpression(Operator.ADD, lhs, rhs), statements
        return BinaryExpression(Operator.SUB, lhs, rhs), statements

    # -------------------
    # NEW: fully constrained relations
    # -------------------
    def simplify_relation_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []

        # Make comparator inputs explicit signals (robust + keeps things clean)
        lhs_sig = self._force_signal(lhs, statements)
        rhs_sig = self._force_signal(rhs, statements)

        if node.op in [IRNodes.Operator.EQU, IRNodes.Operator.NEQ]:
            eq_out, eq_stmts = self._constrained_equ(lhs_sig, rhs_sig)
            statements += eq_stmts
            if node.op == IRNodes.Operator.NEQ:
                neq_out, not_stmts = self._constrained_not(eq_out)
                statements += not_stmts
                return neq_out, statements
            return eq_out, statements

        match node.op:
            case IRNodes.Operator.LTH:
                out, s = self._constrained_comparator("LessThan", lhs_sig, rhs_sig)
                return out, statements + s
            case IRNodes.Operator.LEQ:
                out, s = self._constrained_comparator("LessEqThan", lhs_sig, rhs_sig)
                return out, statements + s
            case IRNodes.Operator.GTH:
                out, s = self._constrained_comparator("GreaterThan", lhs_sig, rhs_sig)
                return out, statements + s
            case IRNodes.Operator.GEQ:
                out, s = self._constrained_comparator("GreaterEqThan", lhs_sig, rhs_sig)
                return out, statements + s
            case _:
                raise NotImplementedError(f"Unexpected relation operator {node.op}")

    def simplify_binary_boolean_logic_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.GATES)

        match node.op:
            case IRNodes.Operator.LAND:
                gate = self._next_component([], CallExpression(Identifier("AND")))
            case IRNodes.Operator.LOR:
                gate = self._next_component([], CallExpression(Identifier("OR")))
            case IRNodes.Operator.LXOR:
                gate = self._next_component([], CallExpression(Identifier("XOR")))
            case _:
                raise NotImplementedError(f"Unexpected operator {node.op}")

        stmts: list[Statement] = [gate]
        a = FieldAccessExpression(gate.name.copy(), Identifier("a"))
        b = FieldAccessExpression(gate.name.copy(), Identifier("b"))
        stmts.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, a, lhs))
        stmts.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, b, rhs))
        out = FieldAccessExpression(gate.name.copy(), Identifier("out"))
        return out, stmts

    def simplify_ternary_expression(self, node: IRNodes.TernaryExpression, cond: Expression, if_expr: Expression, else_expr: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.MUX)
        mux = self._next_component([], CallExpression(Identifier("Mux1")))
        c0 = IndexAccessExpression(FieldAccessExpression(mux.name.copy(), Identifier("c")), IntegerLiteral(0))
        c1 = IndexAccessExpression(FieldAccessExpression(mux.name.copy(), Identifier("c")), IntegerLiteral(1))
        s  = FieldAccessExpression(mux.name.copy(), Identifier("s"))
        out = FieldAccessExpression(mux.name.copy(), Identifier("out"))
        stmts: list[Statement] = [mux]
        stmts.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, c0, else_expr))
        stmts.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, c1, if_expr))
        stmts.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, s, cond))
        return out, stmts

    def simplify_div_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []

        if self._is_at_least_quadratic(lhs):
            lhs_sig = self._next_intermediate_signal()
            statements.append(lhs_sig)
            statements.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, lhs_sig.name.copy(), lhs.copy()))
            lhs = lhs_sig.name.copy()

        if self._is_at_least_quadratic(rhs):
            rhs_sig = self._next_intermediate_signal()
            statements.append(rhs_sig)
            statements.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, rhs_sig.name.copy(), rhs.copy()))
            rhs = rhs_sig.name.copy()

        q = self._next_intermediate_signal()
        statements.append(q)

        # q <-- lhs / rhs;
        statements.append(
            AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, q.name.copy(), BinaryExpression(Operator.DIV, lhs, rhs))
        )
        # q * rhs === lhs;
        statements.append(
            AssignmentOrConstraint(Operator.EQU_CONSTRAINT, BinaryExpression(Operator.MUL, q.name.copy(), rhs.copy()), lhs.copy())
        )
        return q.name.copy(), statements

    def simplify_rem_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        if self.__assertion_mode:
            raise NotImplementedError("REM is not constrained; forbidden inside assertions.")
        signal = self._next_intermediate_signal()
        stmts: list[Statement] = [signal]
        stmts.append(AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, signal.name.copy(), BinaryExpression(Operator.REM, lhs, rhs)))
        return signal.name.copy(), stmts

    def simplify_bitwise_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        if self.__assertion_mode:
            raise NotImplementedError("Bitwise ops are not constrained; forbidden inside assertions.")
        signal = self._next_intermediate_signal()
        stmts: list[Statement] = [signal]
        operator = super().visit_operator(node.op)
        stmts.append(AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, signal.name.copy(), BinaryExpression(operator, lhs, rhs)))
        return signal.name.copy(), stmts

    # -------------------
    # Existing helpers (unchanged)
    # -------------------
    def _is_constant(self, node: Expression) -> bool:
        match node:
            case Identifier():
                return False
            case ConditionalExpression():
                return False
            case BinaryExpression():
                return self._is_constant(node.lhs) and self._is_constant(node.rhs)
            case UnaryExpression():
                return self._is_constant(node.value)
            case CallExpression():
                return False
            case IndexAccessExpression():
                return False
            case FieldAccessExpression():
                return False
            case IntegerLiteral():
                return True
            case StringLiteral():
                return True
            case ListLiteral():
                return all(map(self._is_constant, node.value))
            case _:
                raise NotImplementedError(f"Unexpected Expression '{node.__class__.__name__}'")

    def _contains_variable(self, node: Expression) -> bool:
        match node:
            case Identifier():
                return True
            case ConditionalExpression():
                return self._contains_variable(node.condition) or self._contains_variable(node.trueVal) or self._contains_variable(node.falseVal)
            case BinaryExpression():
                return self._contains_variable(node.lhs) or self._contains_variable(node.rhs)
            case UnaryExpression():
                return self._contains_variable(node.value)
            case CallExpression():
                return True
            case IndexAccessExpression():
                return True
            case FieldAccessExpression():
                return True
            case IntegerLiteral():
                return False
            case StringLiteral():
                return False
            case ListLiteral():
                return any(map(self._contains_variable, node.value))
            case _:
                raise NotImplementedError(f"Unexpected Expression '{node.__class__.__name__}'")

    def _is_at_least_quadratic(self, node: Expression) -> bool:
        match node:
            case Identifier():
                return False
            case ConditionalExpression():
                return self._is_at_least_quadratic(node.condition) \
                    or self._is_at_least_quadratic(node.trueVal) \
                    or self._is_at_least_quadratic(node.falseVal)
            case BinaryExpression():
                return self._is_at_least_quadratic(node.lhs) \
                    or self._is_at_least_quadratic(node.rhs) \
                    or (node.operator in [Operator.MUL, Operator.DIV, Operator.QUO, Operator.REM] and
                        self._contains_variable(node.lhs) and
                        self._contains_variable(node.rhs))
            case UnaryExpression():
                if node.operator == Operator.COMP:
                    return False
                return self._is_at_least_quadratic(node.value)
            case CallExpression():
                return False
            case IndexAccessExpression():
                return False
            case FieldAccessExpression():
                return False
            case IntegerLiteral():
                return False
            case StringLiteral():
                return False
            case ListLiteral():
                return any(map(self._is_at_least_quadratic, node.value))
            case _:
                raise NotImplementedError(f"Unexpected Expression '{node.__class__.__name__}'")

    def _next_intermediate_signal(self) -> SignalDefinition:
        return SignalDefinition(self.__name_dispenser.next("sig"), SignalKind.INTERMEDIATE)

    def _next_component(self, sizes: list[Expression], value: Expression) -> ComponentDefinition:
        return ComponentDefinition(self.__name_dispenser.next("comp"), sizes, value)

    # -------------------
    # circomlib building blocks
    # -------------------
    def _constrained_not(self, value: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.GATES)
        not_gate = self._next_component([], CallExpression(Identifier("NOT")))
        not_in = FieldAccessExpression(not_gate.name.copy(), Identifier("in"))
        not_out = FieldAccessExpression(not_gate.name.copy(), Identifier("out"))
        assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, not_in, value)
        return not_out, [not_gate, assign]

    def _constrained_equ(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.COMPARATORS)
        c = self._next_component([], CallExpression(Identifier("IsEqual")))
        in0 = IndexAccessExpression(FieldAccessExpression(c.name.copy(), Identifier("in")), IntegerLiteral(0))
        in1 = IndexAccessExpression(FieldAccessExpression(c.name.copy(), Identifier("in")), IntegerLiteral(1))
        s: list[Statement] = [c]
        s.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, in0, lhs))
        s.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, in1, rhs))
        out = FieldAccessExpression(c.name.copy(), Identifier("out"))
        return out, s

    def _constrained_is_zero(self, x: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.COMPARATORS)
        c = self._next_component([], CallExpression(Identifier("IsZero")))
        cin = FieldAccessExpression(c.name.copy(), Identifier("in"))
        cout = FieldAccessExpression(c.name.copy(), Identifier("out"))
        s: list[Statement] = [c]
        s.append(AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, cin, x))
        return cout, s

    def _constrained_comparator(
    self,
    template_name: str,
    lhs: Expression,
    rhs: Expression
    ) -> tuple[Expression, list[Statement]]:
        """
        component c = <template_name>(nBits);
        c.in[0] <== lhs;
        c.in[1] <== rhs;
        returns c.out
        """
        self.__dependency_manager.dependencies.add(ImportDependency.COMPARATORS)

        comp = ComponentDefinition(
            name=self.__name_dispenser.next("comp"),
            sizes=[],  # ✅ NO array size
            value=CallExpression(
                Identifier(template_name),
                [IntegerLiteral(self.__comparison_nbits)]  # ✅ constructor argument
            ),
        )

        in0 = IndexAccessExpression(
            FieldAccessExpression(comp.name.copy(), Identifier("in")),
            IntegerLiteral(0)
        )
        in1 = IndexAccessExpression(
            FieldAccessExpression(comp.name.copy(), Identifier("in")),
            IntegerLiteral(1)
        )

        stmts: list[Statement] = [comp]
        stmts.append(
            AssignmentOrConstraint(
                Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT,
                in0,
                lhs
            )
        )
        stmts.append(
            AssignmentOrConstraint(
                Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT,
                in1,
                rhs
            )
        )

        out = FieldAccessExpression(comp.name.copy(), Identifier("out"))
        return out, stmts



# ======================================================================
# NEW: “Constrain ALL assertions” visitor
#  - lowers assertion expressions via IR2ConstraintCircomVisitor
#  - forces predicate to be true (=== 1)
#  - forbids unconstrained ops in assertions (REM/bitwise/COMP)
# ======================================================================
class IR2CircomVisitorConstrainAssertions(IR2CircomVisitor):
    def __init__(self, constraint_assignment_probability: float, rng: Random, unwrap_assertion_probability: float, assertion_nbits: int = 252):
        super().__init__(constraint_assignment_probability, rng)
        self.__unwrap_assertion_probability = unwrap_assertion_probability
        self.__assertion_nbits = assertion_nbits

    def visit_assertion(self, node: IRNodes.Assertion) -> tuple[Statement, list[Statement]]:

        # Sample binomial to possibly keep original boolean assertion
        if not bernoulli(self.__unwrap_assertion_probability, self._IR2CircomVisitor__rng):
            return super().visit_assertion(node)

        # Lower EVERYTHING through constraint-lowerer (splitting included)
        lowerer = IR2ConstraintCircomVisitor(
            self._IR2CircomVisitor__name_dispenser,
            self._IR2CircomVisitor__dependency_manager,
            comparison_nbits=self.__assertion_nbits,
            assertion_mode=True,   # <-- important
        )

        expr, tail = lowerer.visit_expression(node.value)

        # Coerce to boolean predicate (safe even if already boolean):
        # pred := NOT(IsZero(expr))
        isz_out, isz_stmts = lowerer._constrained_is_zero(expr.copy())
        pred, not_stmts = lowerer._constrained_not(isz_out)

        one = IntegerLiteral(1)
        must_be_true = BinaryExpression(Operator.EQU_CONSTRAINT, pred, one)

        return AssertStatement(must_be_true, unwrapped=True), (tail + isz_stmts + not_stmts)