"""
Generator that only produces quadratic assertions using semantic fusion.
This generator allows to change assertions into constraints as it ensurs they are quadratic.
"""

from ..config import IRConfig
from .base import BaseCircuitGenerator
from .base import ExpressionKind
from ..nodes import *
from ...common.field import CurvePrime

class SemanticFusionExpressionKind(StrEnum):
    ADDITION_FUSION       = "ADDITION_FUSION"

class QuadraticCircuitGenerator(BaseCircuitGenerator):
    # internal generation variable tracker
    _assertion_ordering   : int # NOTE: some backends depend on assertion numbering (e.g. noir)
    _assertion_budget     : int
    _unassigned_variables : list[str]
    _preconditions        : list[Assume]

    def __init__ \
        ( self
        , curve_prime: CurvePrime
        , config: IRConfig
        , seed: float | int | None = None
        , exclude_prime : bool = False
        ):

        super().__init__(curve_prime, config, seed, exclude_prime)

        # init internal variable
        self._assertion_budget = 0
        self._assertion_ordering = 0
        self._unassigned_variables = []
        self._preconditions = []
        self._config = config

    def run(self) -> Circuit:
        # Quadratic generator requires at least 1 input variable
        assert self._min_number_of_input_variables >= 1, \
            "Quadratic generator cannot be used with min_number_of_input_variables < 1"
        
        input_variables_amount = self._rng.randint(
            self._min_number_of_input_variables, self._max_number_of_input_variables)
        output_variables_amount = self._rng.randint(
            self._min_number_of_output_variables, self._max_number_of_output_variables)
        
        input_variables = ["in" + str(i) for i in range(input_variables_amount)]
        output_variables = ["out" + str(i) for i in range(output_variables_amount)]
        
        statements = []
        for i in range(len(output_variables)): # For each output variable we do one assertion that constraints it 
            num_inputs_used = self._rng.randint(1, len(input_variables))
            inputs_used = self._rng.sample(input_variables, num_inputs_used)
            out = output_variables[i]

            # Sample which relation to use (<, >, ==)
            relation_type = self._get_random_relation_type()
            # Sample which fusion technique to use (only addition fusion for now)
            semantic_fusion_type = self._get_random_semantic_fusion_type()

            # Create replacement mapping for variables
            replacement_mapping = {}
            for var in inputs_used:
                replacement_mapping[var] = self._get_semantic_inverse(var, semantic_fusion_type, inputs_used, out)

            if relation_type == Operator.EQU:
                expressions = [None, None, None]
                for j in range(3):
                    expressions[j] = self._random_linear_expression(inputs_used)
                    expressions[j] = self._randomly_replace_variables(expressions[j], replacement_mapping)

                fusion_assignment = self._get_fusion_assignment(inputs_used, out, semantic_fusion_type)
                statements.append(fusion_assignment)

                quadratic_expression = self._generate_quadratic_from_linear(expressions[0], expressions[1], expressions[2])
                assertion_expr = BinaryExpression(
                    Operator.EQU,
                    quadratic_expression,
                    Integer(0)
                )
                assertion = Assertion(
                    identifier = f"assertion_{i}",
                    value = assertion_expr
                )
                statements.append(assertion)
            else:
                linear_expr = self._random_linear_expression(inputs_used)
                linear_expr = self._randomly_replace_variables(linear_expr, replacement_mapping)
                fusion_assignment = self._get_fusion_assignment(inputs_used, out, semantic_fusion_type)
                statements.append(fusion_assignment)
                assertion_expr = BinaryExpression(
                    relation_type,
                    linear_expr,
                    Integer(0)
                )
                assertion = Assertion(
                    identifier = f"assertion_{i}",
                    value = assertion_expr
                )
                statements.append(assertion)

        circuit_name = f"circuit_{self._random_id(10)}"
        return Circuit(circuit_name, input_variables, output_variables, statements)
    
    def _random_linear_expression(self, vars_used: list[str]) -> Expression:
        coefficients = [self._random_non_zero_number().value for _ in range(len(vars_used))]

        expr = None
        for i in range(len(vars_used)):
            term = BinaryExpression(
                Operator.MUL,
                Variable(vars_used[i]),
                Integer(coefficients[i])
            )
            if expr is None:
                expr = term
            else:
                expr = BinaryExpression(
                    Operator.ADD,
                    expr,
                    term
                )
        return expr

    def _get_random_semantic_fusion_type(self) -> SemanticFusionExpressionKind:
        return SemanticFusionExpressionKind.ADDITION_FUSION
    
    def _get_random_relation_type(self) -> Operator:
        relations = [
            Operator.EQU,
            Operator.LTH,
            Operator.GTH,   
        ]

        ineq_prob = self._config.generation.quadratic_generator_inequality_assertion_probability
        probabilities = [1.0 - ineq_prob, ineq_prob / 2, ineq_prob / 2]
        return self._rng.choices(relations, probabilities)[0]

    def _get_semantic_inverse(
        self,
        var: str,
        fusion_expr: SemanticFusionExpressionKind,
        vars_used: list[str],
        out_var: str
    ) -> Expression:
        if fusion_expr == SemanticFusionExpressionKind.ADDITION_FUSION:
            # To invert addition fusion, we can express var as:
            # var = out_var - sum(other_vars)
            other_vars = [v for v in vars_used if v != var]
            
            if len(other_vars) == 0:
                # If this is the only variable, var = out_var
                return Variable(out_var)
            
            sum_other_vars = None
            for ov in other_vars:
                term = Variable(ov)
                if sum_other_vars is None:
                    sum_other_vars = term
                else:
                    sum_other_vars = BinaryExpression(
                        Operator.ADD,
                        sum_other_vars,
                        term
                    )
            inverse_expr = BinaryExpression(
                Operator.SUB,
                Variable(out_var),
                sum_other_vars
            )
            return inverse_expr
        else:
            raise NotImplementedError(f"Semantic fusion inverse not implemented for {fusion_expr}")
        
    def _get_fusion_assignment(
        self,
        vars_used: list[str],
        out_var: str,
        fusion_expr: SemanticFusionExpressionKind
    ) -> Expression:
        """
        Assigns the fusion expression to the output variable.
        e.g out0 <== in0 + in1 + in2
        """
        if fusion_expr == SemanticFusionExpressionKind.ADDITION_FUSION:
            rhs = None
            for v in vars_used:
                term = Variable(v)
                if rhs is None:
                    rhs = term
                else:
                    rhs = BinaryExpression(
                        Operator.ADD,
                        rhs,
                        term
                    )

            return Assignment(
                lhs = Variable(out_var),
                rhs = rhs
            )
        else:
            raise NotImplementedError(f"Semantic fusion expression not implemented for {fusion_expr}")

    def _randomly_replace_variables(
        self,
        expr: Expression,
        replacement_mapping: dict[str, Expression]
    ) -> Expression:
        if isinstance(expr, Variable):
            if expr.name in replacement_mapping:
                return replacement_mapping[expr.name]
            else:
                return expr
        elif isinstance(expr, Integer):
            return expr
        elif isinstance(expr, BinaryExpression):
            lhs_replaced = self._randomly_replace_variables(expr.lhs, replacement_mapping)
            rhs_replaced = self._randomly_replace_variables(expr.rhs, replacement_mapping)
            return BinaryExpression(expr.op, lhs_replaced, rhs_replaced)
        elif isinstance(expr, UnaryExpression):
            operand_replaced = self._randomly_replace_variables(expr.operand, replacement_mapping)
            return UnaryExpression(expr.op, operand_replaced)
        else:
            raise NotImplementedError(f"Variable replacement not implemented for expression type {type(expr)}")

    def _generate_quadratic_from_linear(self, expr1: Expression, expr2: Expression, expr3: Expression) -> Expression:
        quadratic_expression = BinaryExpression(
            Operator.MUL,
            expr1,
            expr2
        )
        quadratic_expression = BinaryExpression(
            Operator.ADD,
            quadratic_expression,
            expr3
        )
        return quadratic_expression