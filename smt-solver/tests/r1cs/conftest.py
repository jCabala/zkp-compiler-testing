"""
Shared helpers for building minimal R1CS instances in tests.

R1CS constraint: A * B = C
Each of A, B, C is a linear combination of variables.
Variable index 0 is always the constant-one wire.
"""

from src.r1cs.ir import R1CS, Constraint, LinearCombination, Term, Variable

PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def var(idx: int) -> Variable:
    return Variable(index=idx)


def lc(*terms: tuple[int, int]) -> LinearCombination:
    """Build a LinearCombination from (coeff, var_index) pairs."""
    return LinearCombination(terms=[Term(variable=var(idx), coeff=coeff) for coeff, idx in terms])


def const(c: int) -> LinearCombination:
    """Linear combination representing a constant: c * wire_0."""
    return lc((c, 0))


def make_r1cs(constraints: list[Constraint], nvars: int, bool_wires: set[int] = None) -> R1CS:
    """Build a minimal R1CS for testing with the given constraints."""
    variables = [Variable(index=i) for i in range(nvars)]
    return R1CS(
        n8=32,
        prime=PRIME,
        nVars=nvars,
        nOutputs=0,
        nPubInputs=0,
        nPrvInputs=nvars - 1,
        nLabels=nvars,
        nConstraints=len(constraints),
        useCustomGates=False,
        variables=variables,
        constraints=constraints,
        bool_wire_indices=bool_wires or set(),
    )
