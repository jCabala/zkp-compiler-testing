"""
This is an SMT-LIB core theory (just booleans) implemented using
arithmetic expressions over bits {0,1}. This is helpful for circom programs.
"""

from __future__ import annotations
from typing import Sequence, Union
from zk_ir import *

BoolArg = Union[bool, Expression]

# -----------------------------
# Basic constructors/utilities
# -----------------------------

def _bool_const(v: bool) -> Boolean:
    return Boolean(v)

def _int_const(v: int) -> Integer:
    return Integer(v)

def _as_expr(x: BoolArg) -> Expression:
    if isinstance(x, bool):
        return _bool_const(x)
    if isinstance(x, Expression):
        return x
    raise TypeError(f"Expected bool or Expression, got {type(x)}")

def _as_bit(x: BoolArg) -> Expression:
    """
    Treat a Bool term as a field element bit in {0,1}.
    We don't *enforce* booleanity here (that requires constraints),
    we only build expressions that assume inputs are bits.
    """
    return _as_expr(x)

def _add(a: Expression, b: Expression) -> Expression:
    return BinaryExpression(Operator.ADD, a, b)

def _sub(a: Expression, b: Expression) -> Expression:
    return BinaryExpression(Operator.SUB, a, b)

def _mul(a: Expression, b: Expression) -> Expression:
    return BinaryExpression(Operator.MUL, a, b)

def _equ(a: Expression, b: Expression) -> Expression:
    return BinaryExpression(Operator.EQU, a, b)

def _one() -> Integer:
    return _int_const(1)

def _zero() -> Integer:
    return _int_const(0)

def _two() -> Integer:
    return _int_const(2)

def _is_bool_literal(e: Expression) -> bool:
    return isinstance(e, Boolean)

def _bool_value(e: Expression) -> bool:
    assert isinstance(e, Boolean)
    return e.value

# -----------------------------
# Boolean gate expressions
# -----------------------------

def core_not(a: BoolArg) -> Expression:
    """
    Logical NOT as an arithmetic equation on bits:
    not(a) = 1 - a  (valid when a in {0,1}).
    """
    Neg

def core_and(*args: BoolArg) -> Expression:
    pass

def core_or(*args: BoolArg) -> Expression:
   pass

def core_xor(*args: BoolArg) -> Expression:
    pass

def core_implies(a: BoolArg, b: BoolArg) -> Expression:
    pass

def core_eq(*args: BoolArg) -> Expression:
    pass

def core_distinct(*args: BoolArg) -> Expression:
    pass

def core_ite(cond: BoolArg, if_t: BoolArg, if_f: BoolArg) -> Expression:
    pass

# -----------------------------
# Booleanity / assertions
# -----------------------------

def core_is_bit(x: BoolArg) -> Expression:
    b = _as_bit(x)
    """
    Enforce booleanity of a field element b via the quadratic equation:
    b * (b - 1) == 0
    This has solutions b in {0,1}.
    """
    return _equ(_mul(b, _sub(b, _one())), _zero())

def core_assert_true(phi: BoolArg, identifier: str = "assert") -> Assertion:
    p = _as_bit(phi)
    """
    Create an assertion that a proposition p is true by equating to 1:
    p == 1.
    """
    return Assertion(identifier, _equ(p, _one()))

def core_assume_true(phi: BoolArg, identifier: str = "assume") -> Assume:
    p = _as_bit(phi)
    """
    Create an assumption that a proposition p is true by equating to 1:
    p == 1.
    """
    return Assume(_equ(p, _one()), identifier)

# -----------------------------
# CNF helpers
# -----------------------------

def core_clause(*lits: BoolArg) -> Expression:
    return core_or(*lits)

def core_cnf(*clauses: Sequence[BoolArg]) -> Expression:
    return core_and(*(core_or(*cl) for cl in clauses))
