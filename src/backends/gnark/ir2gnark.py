import src.smt_lib.zk_ir as IRNodes

from .nodes import *

MAX_64_BITS_INTEGER = (1 << 64) - 1


class IR2GnarkVisitor:
    """
    NOTE:
        - circuit variables are replaced by "FVar_{name}"
        - circuit names are manipulated to contain a starting "C"
        - relations are implemented using a subset of relations

        PATCH:
        - outputs are circuit members (struct fields), NOT local vars.
        - output references are `circuit.FVar_<name>`
        - output assignments are normal assignments (no := local definitions)

        NEW:
        - preserve input/output information in circuit fields by using `is_public=True`
          for outputs (so gnark tags them `gnark:",public"`).
        - annotate inputs/outputs/labels for sr1cs generation via helper calls:
            CircuitVarIn(circuit.FVar_x)
            CircuitVarOut(circuit.FVar_y)
            Label(circuit.FVar_x, "x")
            Label(circuit.FVar_y, "y")
        - constrain booleans for BOTH inputs and outputs (fixes TODO)

        - TODO: enable AssertIsDifferent again
        - TODO: think about modeling integers as big.NewInt(...)
        - TODO: deal with different assertion types
    """

    __temporary_variables: int

    def __init__(self):
        self.__temporary_variables = 0

    def transform(self, system: IRNodes.Circuit) -> CircuitDefinitionCollection:
        return self.visit_circuit(system)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

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

    def visit_statement(self, node: IRNodes.IRNode) -> tuple[Statement | None, list[Statement]]:
        match node:
            case IRNodes.Assertion():
                return self.visit_assertion(node)
            case IRNodes.Assignment():
                return self.visit_assignment(node)
            case IRNodes.Assume():
                return self.visit_assume(node)
            case _:
                raise NotImplementedError()

    # ------------------------------------------------------------------
    # Variables: everything is a circuit member now (inputs AND outputs)
    # ------------------------------------------------------------------

    def visit_variable(self, node: IRNodes.Variable) -> tuple[Expression, list[Statement]]:
        return FieldAccessExpression(Identifier("circuit"), f"FVar_{node.name}"), []

    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        return (Literal(1) if node.value else Literal(0)), []

    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        return self._new_big_int(node.value)

    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        expr, statements = self.visit_expression(node.value)
        if node.op == IRNodes.Operator.SUB:
            return self._neg(expr), statements
        if node.op == IRNodes.Operator.NOT and node.is_boolean_expression():
            return self._is_zero(expr), statements
        raise NotImplementedError(f"Unary expression is not supported '{node}'")

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        match node.op:
            case IRNodes.Operator.MUL:
                return self._mul(lhs, rhs), statements
            case IRNodes.Operator.ADD:
                return self._add(lhs, rhs), statements
            case IRNodes.Operator.SUB:
                return self._sub(lhs, rhs), statements
            case IRNodes.Operator.EQU:
                return self._eq(lhs, rhs), statements
            case IRNodes.Operator.LTH:
                return self._lth(lhs, rhs), statements
            case IRNodes.Operator.LEQ:
                return self._leq(lhs, rhs), statements
            case IRNodes.Operator.GTH:
                return self._gth(lhs, rhs), statements
            case IRNodes.Operator.GEQ:
                return self._geq(lhs, rhs), statements
            case IRNodes.Operator.NEQ:
                return self._neq(lhs, rhs), statements
            case IRNodes.Operator.LAND:
                return self._and(lhs, rhs), statements
            case IRNodes.Operator.LOR:
                return self._or(lhs, rhs), statements
            case IRNodes.Operator.LXOR:
                return self._xor(lhs, rhs), statements
            case IRNodes.Operator.DIV:
                return self._div(lhs, rhs), statements
            case IRNodes.Operator.AND:
                bitwise_expr, bitwise_stmts = self._bitwise_and(lhs, rhs)
                statements += bitwise_stmts
                return bitwise_expr, statements
            case IRNodes.Operator.OR:
                bitwise_expr, bitwise_stmts = self._bitwise_or(lhs, rhs)
                statements += bitwise_stmts
                return bitwise_expr, statements
            case IRNodes.Operator.XOR:
                bitwise_expr, bitwise_stmts = self._bitwise_xor(lhs, rhs)
                statements += bitwise_stmts
                return bitwise_expr, statements
            case _:
                raise NotImplementedError(f"binary operator {node.op.value}")

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []
        cond, cond_tail = self.visit_expression(node.condition)
        statements += cond_tail
        if_expr, if_expr_tail = self.visit_expression(node.if_expr)
        statements += if_expr_tail
        else_expr, else_expr_tail = self.visit_expression(node.else_expr)
        statements += else_expr_tail
        return self._select(cond, if_expr, else_expr), statements

    def visit_assertion(self, node: IRNodes.Assertion) -> tuple[Statement, list[Statement]]:
        return self._visit_as_assertion_content(node.value)

    # ------------------------------------------------------------------
    # Assignments: always normal assignments (no :=)
    # ------------------------------------------------------------------

    def visit_assignment(self, node: IRNodes.Assignment) -> tuple[Statement, list[Statement]]:
        statements: list[Statement] = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        assignment = AssignStatement(lhs, rhs, is_definition=False)
        return assignment, statements

    def visit_assume(self, node: IRNodes.Assume) -> tuple[Statement, list[Statement]]:
        return self._visit_as_assertion_content(node.condition)

    # ------------------------------------------------------------------
    # Circuit: preserve IO in struct fields + emit IO annotations + fix TODO
    # ------------------------------------------------------------------

    def visit_circuit(self, node: IRNodes.Circuit) -> CircuitDefinitionCollection:
        # Preserve IO information in the Go struct:
        # - inputs: private (witness) fields
        # - outputs: mark as public (so gnark tags them `gnark:",public"`)
        #
        # If you later want only some outputs public, adjust here.
        circuit_fields = (
            [CircuitStructField(f"FVar_{e.name}", False) for e in node.inputs]
            + [CircuitStructField(f"FVar_{e.name}", True) for e in node.outputs]
        )

        circuit_struct = CircuitStruct(node.name, circuit_fields)

        circuit_function_stmts: list[Statement] = []

        # --------------------------------------------------------------
        # NEW: annotate inputs/outputs/labels for sr1cs dumping
        # (prefix.go provides CircuitVarIn/CircuitVarOut/Label)
        # --------------------------------------------------------------
        for v in node.inputs:
            vref = FieldAccessExpression(Identifier("circuit"), f"FVar_{v.name}")
            circuit_function_stmts.append(self._helper_stmt("CircuitVarIn", [vref.copy()]))
            circuit_function_stmts.append(self._helper_stmt("Label", [vref.copy(), Literal(v.name)]))

        for v in node.outputs:
            vref = FieldAccessExpression(Identifier("circuit"), f"FVar_{v.name}")
            circuit_function_stmts.append(self._helper_stmt("CircuitVarOut", [vref.copy()]))
            circuit_function_stmts.append(self._helper_stmt("Label", [vref.copy(), Literal(v.name)]))

        # --------------------------------------------------------------
        # Fix TODO: constrain boolean-ness for ALL declared boolean vars,
        # not just inputs. (inputs + outputs)
        # --------------------------------------------------------------
        for v in list(node.inputs) + list(node.outputs):
            if v.variable_type == IRNodes.VariableType.BOOLEAN:
                vref = FieldAccessExpression(Identifier("circuit"), f"FVar_{v.name}")
                circuit_function_stmts.append(self._assert_is_boolean(vref))

        # translate body
        for statement in node.statements:
            stmt, tail = self.visit_statement(statement)
            if stmt:
                circuit_function_stmts += tail
                circuit_function_stmts.append(stmt)

        # optional debug prints (keep as you had)
        for e in node.outputs:
            out_ref = FieldAccessExpression(Identifier("circuit"), f"FVar_{e.name}")
            circuit_function_stmts.append(self._print([Literal(f"{e.name}:"), out_ref]))

        circuit_define = CircuitDefineFunction(node.name, circuit_function_stmts)

        return CircuitDefinitionCollection(node.name, circuit_struct, circuit_define)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _assert_is_boolean(self, v: Expression) -> Statement:
        return self._api_stmt("AssertIsBoolean", [v])

    def _assert(self, value: Expression) -> Statement:
        return self._assert_eq(value, Literal(1))

    def _eq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._is_zero(self._cmp(lhs, rhs))

    def _neq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._is_zero(self._eq(lhs, rhs))

    def _gth(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._eq(self._cmp(lhs, rhs), Literal(1))

    def _geq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._is_zero(self._lth(lhs, rhs))

    def _visit_as_assertion_content(self, value: IRNodes.Expression) -> tuple[Statement, list[Statement]]:
        if isinstance(value, IRNodes.BinaryExpression):
            statements: list[Statement] = []
            lhs_expr, lhs_stmts = self.visit_expression(value.lhs)
            statements += lhs_stmts
            rhs_expr, rhs_stmts = self.visit_expression(value.rhs)
            statements += rhs_stmts
            match value.op:
                case IRNodes.Operator.EQU:
                    return self._assert_eq(lhs_expr, rhs_expr), statements
                case IRNodes.Operator.LEQ:
                    return self._assert_le(lhs_expr, rhs_expr), statements
                case IRNodes.Operator.GEQ:
                    return self._assert_le(rhs_expr, lhs_expr), statements
                case IRNodes.Operator.NEQ:
                    return self._assert_ne(lhs_expr, rhs_expr), statements
                case _:
                    pass

        expr, statements = self.visit_expression(value)
        return self._assert(expr), statements

    # ------------------------------------------------------------------
    # API wrapper functions (api.*)
    # ------------------------------------------------------------------

    def _api_expr(self, func: str, args: list[Expression]) -> CallExpression:
        return CallExpression(FieldAccessExpression(Identifier("api"), func), args)

    def _api_stmt(self, func: str, args: list[Expression]) -> CallStatement:
        return CallStatement(self._api_expr(func, args))

    # NEW: helper calls (global functions, not methods on api)
    def _helper_stmt(self, func: str, args: list[Expression]) -> CallStatement:
        return CallStatement(CallExpression(Identifier(func), args))

    # Arithmetic wrappers

    def _add(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Add", [lhs, rhs])

    def _mulacc(self, a: Expression, b: Expression, c: Expression) -> Expression:
        return self._api_expr("MulAcc", [a, b, c])

    def _neg(self, value: Expression) -> Expression:
        return self._api_expr("Neg", [value])

    def _sub(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Sub", [lhs, rhs])

    def _mul(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Mul", [lhs, rhs])

    def _div_unchecked(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("DivUnchecked", [lhs, rhs])

    def _div(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Div", [lhs, rhs])

    def _inv(self, value: Expression) -> Expression:
        return self._api_expr("Inverse", [value])

    # Bit Operations Wrapper (variable must be 0 or 1)

    def _xor(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Xor", [lhs, rhs])

    def _or(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Or", [lhs, rhs])

    def _and(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("And", [lhs, rhs])

    # Conditionals Wrapper

    def _select(self, cond: Expression, if_expr: Expression, else_expr: Expression) -> Expression:
        return self._api_expr("Select", [cond, if_expr, else_expr])

    # Is Zero Wrapper

    def _is_zero(self, value: Expression) -> Expression:
        return self._api_expr("IsZero", [value])

    # Comparator Wrapper

    def _cmp(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._api_expr("Cmp", [lhs, rhs])

    # Assertion Wrapper

    def _assert_eq(self, lhs: Expression, rhs: Expression) -> Statement:
        return self._api_stmt("AssertIsEqual", [lhs, rhs])

    def _assert_ne(self, lhs: Expression, rhs: Expression) -> Statement:
        return self._api_stmt("AssertIsDifferent", [lhs, rhs])

    def _assert_le(self, lhs: Expression, rhs: Expression) -> Statement:
        return self._api_stmt("AssertIsLessOrEqual", [lhs, rhs])

    # Helper wrapper

    def _print(self, values: list[Expression]) -> Statement:
        return self._api_stmt("Println", values)

    def _compiler(self) -> Statement:
        return self._api_stmt("Compiler", [])

    # ------------------------------------------------------------------
    # cmp package functions
    # ------------------------------------------------------------------

    def _cmp_expr(self, func: str, args: list[Expression]) -> CallExpression:
        return CallExpression(FieldAccessExpression(Identifier("cmp"), func), [Identifier("api")] + args)

    def _lth(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._cmp_expr("IsLess", [lhs, rhs])

    def _leq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._cmp_expr("IsLessOrEqual", [lhs, rhs])

    # ------------------------------------------------------------------
    # bits package
    # ------------------------------------------------------------------

    def _bits_expr(self, func: str, args: list[Expression]) -> Expression:
        return CallExpression(FieldAccessExpression(Identifier("bits"), func), [Identifier("api")] + args)

    def _to_binary(self, value: Expression) -> Expression:
        return self._bits_expr("ToBinary", [value])

    def _from_binary(self, value: Expression) -> Expression:
        return self._bits_expr("FromBinary", [value])

    # ------------------------------------------------------------------
    # bitwise helper
    # ------------------------------------------------------------------

    def _to_binary_as_stmt(self, value: Expression) -> tuple[Identifier, list[Statement]]:
        name = self._dispense_tmp_identifier("bits")
        expr = self._to_binary(value)
        stmt = AssignStatement(name, expr, is_definition=True)
        return name.copy(), [stmt]

    def _from_binary_as_stmt(self, value: Expression) -> tuple[Identifier, list[Statement]]:
        name = self._dispense_tmp_identifier("res")
        expr = self._from_binary(value)
        stmt = AssignStatement(name, expr, is_definition=True)
        return name.copy(), [stmt]

    def _field_bit_len(self) -> Expression:
        compiler = CallExpression(FieldAccessExpression(Identifier("api"), "Compiler"), [])
        return CallExpression(FieldAccessExpression(compiler, "FieldBitLen"), [])

    def _bitwise_wrapper(self, lhs: Expression, rhs: Expression, api_func: str) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []

        lhs2bin_var, lhs2bin_stmt = self._to_binary_as_stmt(lhs)
        statements += lhs2bin_stmt
        rhs2bin_var, rhs2bin_stmt = self._to_binary_as_stmt(rhs)
        statements += rhs2bin_stmt

        body: list[Statement] = []
        lhs_bit = IndexAccessExpression(lhs2bin_var, Identifier("i"))
        rhs_bit = IndexAccessExpression(rhs2bin_var, Identifier("i"))
        bit_expr = self._api_expr(api_func, [lhs_bit, rhs_bit])
        body.append(AssignStatement(lhs_bit.copy(), bit_expr, is_definition=False))

        statements.append(ForLoop(Literal(0), self._field_bit_len(), body, "i"))

        result, from_bin_stmt = self._from_binary_as_stmt(lhs2bin_var.copy())
        statements += from_bin_stmt

        return result, statements

    def _bitwise_or(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._bitwise_wrapper(lhs, rhs, "Or")

    def _bitwise_and(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._bitwise_wrapper(lhs, rhs, "And")

    def _bitwise_xor(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._bitwise_wrapper(lhs, rhs, "Xor")

    # ------------------------------------------------------------------
    # temporary helpers
    # ------------------------------------------------------------------

    def _dispense_tmp_name(self, prefix: str = "tmp") -> str:
        name = f"{prefix}_{self.__temporary_variables}"
        self.__temporary_variables += 1
        return name

    def _dispense_tmp_identifier(self, prefix: str = "tmp") -> Identifier:
        return Identifier(self._dispense_tmp_name(prefix=prefix))

    # ------------------------------------------------------------------
    # big int helpers
    # ------------------------------------------------------------------

    def _new_big_int(self, value: int) -> tuple[Identifier, list[Statement]]:
        identifier = self._dispense_tmp_identifier("cons")

        intId = FieldAccessExpression(Identifier("big"), "Int")
        newExpr = CallExpression(Identifier("new"), [intId])
        declaration = AssignStatement(identifier, newExpr, True)

        if value <= MAX_64_BITS_INTEGER:
            setMethod = FieldAccessExpression(identifier.copy(), "SetUint64")
            setMethodExpr = CallExpression(setMethod, [Literal(value)])
        else:
            setMethod = FieldAccessExpression(identifier.copy(), "SetString")
            setMethodExpr = CallExpression(setMethod, [Literal(str(value)), Literal(10)])

        definition = CallStatement(setMethodExpr)

        return identifier.copy(), [declaration, definition]
