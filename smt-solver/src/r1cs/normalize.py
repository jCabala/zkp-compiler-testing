"""
Polynomial normalization for R1CS constraints.

Converts R1CS constraints A * B = C into normalized polynomial form:
  A * B - C = 0 (mod p)

This canonical representation eliminates symmetry issues and makes
pattern detection much simpler.
"""

from typing import Dict, Tuple, List, FrozenSet
from dataclasses import dataclass
from src.r1cs.ir import Constraint, LinearCombination


# Represent a monomial as a frozenset of variable indices (for products)
# E.g., x*y → frozenset({2, 3}), x → frozenset({2}), constant → frozenset()
Monomial = FrozenSet[int]


@dataclass
class NormalizedPoly:
    """
    Polynomial in normalized form: Σ coeff_i * monomial_i = 0 (mod p)
    
    A monomial is a product of variables represented as a frozenset of indices.
    Examples:
      - constant term: frozenset() → coefficient
      - x (var 2): frozenset({2}) → coefficient
      - x*y (vars 2,3): frozenset({2, 3}) → coefficient
      - x² (var 2): frozenset({2, 2}) → wait, frozenset doesn't allow duplicates!
      
    For squared terms, we use a tuple instead to preserve multiplicity.
    Actually, let's use tuple for all monomials to handle powers.
    """
    terms: Dict[Tuple[int, ...], int]  # sorted tuple of var indices → coefficient
    prime: int
    
    def degree(self, monomial: Tuple[int, ...]) -> int:
        """Return the degree of a monomial (number of variables in the product)."""
        return len(monomial)
    
    def get_degree_1_terms(self) -> Dict[int, int]:
        """Get all degree-1 terms (linear terms): var_index → coefficient."""
        return {
            mono[0]: coeff 
            for mono, coeff in self.terms.items() 
            if len(mono) == 1
        }
    
    def get_degree_2_terms(self) -> Dict[Tuple[int, int], int]:
        """Get all degree-2 terms (products): (var1, var2) → coefficient."""
        return {
            (mono[0], mono[1]): coeff
            for mono, coeff in self.terms.items()
            if len(mono) == 2
        }
    
    def get_constant_term(self) -> int:
        """Get the constant term (degree 0)."""
        return self.terms.get((), 0)


def normalize_constraint(constraint: Constraint, p: int) -> NormalizedPoly:
    """
    Convert R1CS constraint A * B = C into normalized polynomial form.
    
    Returns polynomial representing: A * B - C = 0 (mod p)
    
    Steps:
    1. Expand A * B (multiply two linear combinations)
    2. Subtract C
    3. Collect like terms and reduce mod p
    """
    terms: Dict[Tuple[int, ...], int] = {}
    
    # Expand A * B
    # A = Σ a_i * x_i, B = Σ b_j * y_j
    # A * B = Σ (a_i * b_j) * (x_i * y_j)
    for term_a in constraint.A.terms:
        for term_b in constraint.B.terms:
            # Create monomial: product of two variables
            var_a = term_a.variable.index
            var_b = term_b.variable.index
            coeff = (term_a.coeff * term_b.coeff) % p
            
            # Create monomial (sorted tuple for canonical form)
            if var_a == 0 and var_b == 0:
                # Constant * constant → constant term
                monomial = ()
            elif var_a == 0:
                # Constant * var_b → var_b
                monomial = (var_b,)
            elif var_b == 0:
                # var_a * constant → var_a
                monomial = (var_a,)
            else:
                # var_a * var_b → sorted product
                monomial = tuple(sorted([var_a, var_b]))
            
            # Add to polynomial
            if monomial in terms:
                terms[monomial] = (terms[monomial] + coeff) % p
            else:
                terms[monomial] = coeff
    
    # Subtract C
    # -C = Σ (-c_i) * x_i
    for term_c in constraint.C.terms:
        var_c = term_c.variable.index
        coeff = (-term_c.coeff) % p
        
        # Create monomial
        if var_c == 0:
            monomial = ()
        else:
            monomial = (var_c,)
        
        # Add to polynomial
        if monomial in terms:
            terms[monomial] = (terms[monomial] + coeff) % p
        else:
            terms[monomial] = coeff
    
    # Remove zero coefficients
    terms = {mono: coeff for mono, coeff in terms.items() if coeff != 0}
    
    return NormalizedPoly(terms=terms, prime=p)
