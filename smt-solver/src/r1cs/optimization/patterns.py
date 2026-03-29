"""
Pattern detection on normalized polynomials.

All patterns work on the canonical form: Σ ai * monomial_i = 0 (mod p)
This eliminates symmetry issues in R1CS constraints.
"""

from typing import Set, Tuple
from src.r1cs.optimization.normalize import NormalizedPoly


def detect_bool_assignment(poly: NormalizedPoly, bool_wires: Set[int]) -> Set[int]:
    """
    Pattern: x - y = 0  →  x = y
    
    Normalized form: 1*x + (-1)*y = 0
    
    If one variable is boolean, propagate to the other.
    """
    result = set()
    
    # Check: exactly 2 degree-1 terms, no other terms
    if len(poly.terms) != 2:
        return result
    
    deg1_terms = poly.get_degree_1_terms()
    if len(deg1_terms) != 2:
        return result
    
    # Get the two variables and coefficients
    vars_coeffs = list(deg1_terms.items())
    v1, c1 = vars_coeffs[0]
    v2, c2 = vars_coeffs[1]
    
    # Coefficients should be negatives: c1 + c2 ≡ 0 (mod p)
    if (c1 + c2) % poly.prime != 0:
        return result
    
    # Propagate boolean property
    if v1 in bool_wires and v2 not in bool_wires:
        result.add(v2)
    elif v2 in bool_wires and v1 not in bool_wires:
        result.add(v1)
    
    return result


def detect_bool_constraint(poly: NormalizedPoly) -> Set[int]:
    """
    Pattern: x² - x = 0  →  x*(x-1) = 0  →  x is boolean
    
    Normalized form: 1*x² + (-1)*x = 0
    """
    result = set()
    
    # Check: exactly 2 terms, one degree-2, one degree-1
    if len(poly.terms) != 2:
        return result
    
    deg1_terms = poly.get_degree_1_terms()
    deg2_terms = poly.get_degree_2_terms()
    
    if len(deg1_terms) != 1 or len(deg2_terms) != 1:
        return result
    
    # Get the terms
    v1, c1 = list(deg1_terms.items())[0]
    (v2a, v2b), c2 = list(deg2_terms.items())[0]
    
    # The degree-2 term must be x*x (same variable twice)
    if v2a != v2b:
        return result
    
    v2 = v2a
    
    # Must be the same variable in both terms
    if v1 != v2:
        return result
    
    # Coefficients should be negatives: c1 + c2 ≡ 0 (mod p)
    if (c1 + c2) % poly.prime != 0:
        return result
    
    result.add(v1)
    return result


def detect_bool_multiplication(poly: NormalizedPoly, bool_wires: Set[int]) -> Set[int]:
    """
    Pattern: x*y - z = 0  →  x*y = z
    
    If x, y are boolean → z is boolean
    
    Also handles factorization pattern: v*x - v = 0 → v*(x-1) = 0
    If x is boolean, then v must be boolean too.
    """
    result = set()
    
    # Check: exactly 2 terms, one degree-2, one degree-1
    if len(poly.terms) != 2:
        return result
    
    deg1_terms = poly.get_degree_1_terms()
    deg2_terms = poly.get_degree_2_terms()
    
    if len(deg1_terms) != 1 or len(deg2_terms) != 1:
        return result
    
    # Get the terms
    vz, cz = list(deg1_terms.items())[0]
    (vx, vy), cxy = list(deg2_terms.items())[0]
    
    # Coefficients should be negatives: cxy + cz ≡ 0 (mod p)
    if (cxy + cz) % poly.prime != 0:
        return result
    
    # Pattern 1: x*y = z (x and y different, both boolean)
    if vx != vy and vx != vz and vy != vz:
        # If both vx and vy are boolean, then vz is boolean
        if vx in bool_wires and vy in bool_wires:
            result.add(vz)
        return result
    
    # Pattern 2: v*x - v = 0 → v*(x-1) = 0
    # Check if one variable in degree-2 matches the degree-1 variable
    if vz == vx or vz == vy:
        # vz is the repeated variable, find the other one
        other_var = vy if vz == vx else vx
        
        # If other_var is boolean, then vz must be boolean
        # Because: vz*(other_var - 1) = 0, and if other_var ∈ {0,1}, then vz ∈ {0,1}
        if other_var in bool_wires and vz not in bool_wires:
            result.add(vz)
    
    return result


def detect_bool_negation(poly: NormalizedPoly, bool_wires: Set[int]) -> Set[int]:
    """
    Pattern: x + y - 1 = 0  →  x + y = 1
    
    Normalized form: 1*x + 1*y + (-1) = 0
    
    If one variable is boolean, the other is too.
    """
    result = set()
    
    # Check: exactly 3 terms - two degree-1, one constant
    if len(poly.terms) != 3:
        return result
    
    deg1_terms = poly.get_degree_1_terms()
    const = poly.get_constant_term()
    
    if len(deg1_terms) != 2 or const == 0:
        return result
    
    # Get the two variables and coefficients
    vars_coeffs = list(deg1_terms.items())
    v1, c1 = vars_coeffs[0]
    v2, c2 = vars_coeffs[1]
    
    # Both coefficients should be the same
    if c1 != c2:
        return result
    
    # Constant should be negative of the coefficient: c1 + const ≡ 0 (mod p)
    if (c1 + const) % poly.prime != 0:
        return result
    
    # Propagate boolean property
    if v1 in bool_wires and v2 not in bool_wires:
        result.add(v2)
    elif v2 in bool_wires and v1 not in bool_wires:
        result.add(v1)
    
    return result


def detect_ternary_pattern(poly: NormalizedPoly, bool_wires: Set[int]) -> Set[int]:
    """
    Pattern: v1 - v2 - v3 = 0  →  v1 = v2 + v3
    
    Normalized form: 1*v1 + (-1)*v2 + (-1)*v3 = 0
    
    If any 2 of {v1, v2, v3} are boolean, the third is ternary (values in {p-1, 0, 1}).
    
    Common pattern: when v1, v2 are boolean and v1 = v2 + v3,
    then v3 can only be -1, 0, or 1 (represented as p-1, 0, 1 in finite field).
    """
    result = set()
    
    # Check: exactly 3 degree-1 terms, no other terms
    if len(poly.terms) != 3:
        return result
    
    deg1_terms = poly.get_degree_1_terms()
    if len(deg1_terms) != 3:
        return result
    
    # Get variables and coefficients
    vars_coeffs = list(deg1_terms.items())
    
    # Find terms with same absolute coefficient value
    # Look for pattern: one with coeff c, two with coeff -c
    coeffs = [c % poly.prime for _, c in vars_coeffs]
    
    # Count occurrences of each coefficient
    from collections import Counter
    coeff_counts = Counter(coeffs)
    
    # We need exactly two distinct coefficient values (c and -c mod p)
    if len(coeff_counts) != 2:
        return result
    
    # One should appear once, the other twice
    counts = sorted(coeff_counts.values())
    if counts != [1, 2]:
        return result
    
    # Find which coefficient appears once (this is the "positive" one)
    pos_coeff = [c for c, count in coeff_counts.items() if count == 1][0]
    neg_coeff = [c for c, count in coeff_counts.items() if count == 2][0]
    
    # Verify they're negatives: pos_coeff + neg_coeff ≡ 0 (mod p)
    if (pos_coeff + neg_coeff) % poly.prime != 0:
        return result
    
    # Identify variables
    v_pos = [v for v, c in vars_coeffs if c % poly.prime == pos_coeff][0]
    v_negs = [v for v, c in vars_coeffs if c % poly.prime == neg_coeff]
    
    # Check if exactly 2 of the 3 variables are boolean
    all_vars = [v_pos] + v_negs
    bool_count = sum([v in bool_wires for v in all_vars])
    
    if bool_count == 2:
        # The non-boolean variable becomes ternary
        for v in all_vars:
            if v not in bool_wires:
                result.add(v)
                break
    
    return result
