from .nodes import (
    Assertion, Assignment, BinaryExpression, Boolean, Circuit,
    Expression, Integer, TernaryExpression, UnaryExpression, Variable,
)


def _collect_vars(expr: Expression) -> set[str]:
    match expr:
        case Variable():
            return {expr.name}
        case Integer() | Boolean():
            return set()
        case UnaryExpression():
            return _collect_vars(expr.value)
        case BinaryExpression():
            return _collect_vars(expr.lhs) | _collect_vars(expr.rhs)
        case TernaryExpression():
            return (
                _collect_vars(expr.condition)
                | _collect_vars(expr.if_expr)
                | _collect_vars(expr.else_expr)
            )
        case _:
            return set()


def count_connected_assertions(circuit: Circuit) -> tuple[int, int]:
    """
    Returns (connected, disconnected) counts for the circuit's assertions.
    An assertion is connected iff it transitively depends on at least one input signal.
    """
    input_signals: set[str] = set(circuit.inputs)

    assign_deps: dict[str, set[str]] = {
        a.lhs.name: _collect_vars(a.rhs)
        for a in circuit.assignments()
    }

    def reaches_input(start_vars: set[str]) -> bool:
        visited: set[str] = set()
        frontier = set(start_vars)
        while frontier:
            var = frontier.pop()
            if var in visited:
                continue
            visited.add(var)
            if var in input_signals:
                return True
            frontier |= assign_deps.get(var, set()) - visited
        return False

    connected = 0
    disconnected = 0
    for assertion in circuit.assertions():
        if reaches_input(_collect_vars(assertion.value)):
            connected += 1
        else:
            disconnected += 1

    return connected, disconnected
