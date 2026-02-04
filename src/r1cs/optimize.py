"""
R1CS optimization passes.

Analyzes R1CS constraints and propagates boolean properties to additional wires.
All optimizations are sound in finite field arithmetic.

Uses polynomial normalization for clean, symmetric pattern detection.
"""

from typing import Set
from src.r1cs.ir import R1CS
from src.r1cs.normalize import normalize_constraint
from src.r1cs.patterns import (
    detect_bool_assignment,
    detect_bool_constraint,
    detect_bool_multiplication,
    detect_bool_negation,
    detect_ternary_pattern,
)


def optimize_r1cs(r1cs: R1CS, with_logs: bool = False) -> R1CS:
    """
    Apply optimization passes to R1CS.
    
    Currently implements:
    - Boolean propagation: Detects patterns where variables must be boolean (0 or 1)
    - Ternary propagation: Detects patterns where variables must be ternary (p-1, 0, or 1)
    
    Args:
        r1cs: Input R1CS structure
        with_logs: Enable logging of optimizations
        
    Returns:
        R1CS with optimized bool_wire_indices and ternary_wire_indices
    """
    initial_bool_count = len(r1cs.bool_wire_indices)
    initial_ternary_count = len(r1cs.ternary_wire_indices)
    
    # Run propagation until fixpoint
    bool_wires = set(r1cs.bool_wire_indices)
    ternary_wires = set(r1cs.ternary_wire_indices)
    iteration = 0
    
    while True:
        iteration += 1
        old_bool_size = len(bool_wires)
        old_ternary_size = len(ternary_wires)
        
        bool_wires, ternary_wires = _propagate_constraints_once(r1cs, bool_wires, ternary_wires)
        
        # Fixpoint reached when no changes
        if len(bool_wires) == old_bool_size and len(ternary_wires) == old_ternary_size:
            break
    
    if with_logs:
        propagated_bool = bool_wires - r1cs.bool_wire_indices
        propagated_ternary = ternary_wires - r1cs.ternary_wire_indices
        
        if len(propagated_bool) > 0:
            print(f"Boolean optimization: propagated {len(propagated_bool)} additional wires in {iteration} iterations")
        else:
            print(f"Boolean optimization: no additional wires propagated")
        print(f"  Initial: {sorted(r1cs.bool_wire_indices)}")
        if len(propagated_bool) > 0:
            print(f"  Propagated: {sorted(propagated_bool)}")
        print(f"  Total: {sorted(bool_wires)}")
        
        if len(propagated_ternary) > 0:
            print(f"Ternary optimization: propagated {len(propagated_ternary)} additional wires in {iteration} iterations")
            print(f"  Initial: {sorted(r1cs.ternary_wire_indices)}")
            print(f"  Propagated: {sorted(propagated_ternary)}")
            print(f"  Total: {sorted(ternary_wires)}")
    
    # Create new R1CS with updated wire indices
    from dataclasses import replace
    return replace(r1cs, bool_wire_indices=bool_wires, ternary_wire_indices=ternary_wires)


def _propagate_constraints_once(r1cs: R1CS, bool_wires: Set[int], ternary_wires: Set[int]) -> tuple[Set[int], Set[int]]:
    """
    Single pass of constraint propagation through all constraints.
    
    Uses polynomial normalization for clean pattern detection.
    
    Returns (updated_bool_wires, updated_ternary_wires).
    """
    new_bool_wires = set(bool_wires)
    new_ternary_wires = set(ternary_wires)
    p = r1cs.prime
    
    for constraint in r1cs.constraints:
        # Normalize constraint to polynomial form: A*B - C = 0
        poly = normalize_constraint(constraint, p)
        
        # Apply all pattern detectors
        new_bool_wires.update(detect_bool_assignment(poly, new_bool_wires))
        new_bool_wires.update(detect_bool_constraint(poly))
        new_bool_wires.update(detect_bool_multiplication(poly, new_bool_wires))
        new_bool_wires.update(detect_bool_negation(poly, new_bool_wires))
        new_ternary_wires.update(detect_ternary_pattern(poly, new_bool_wires))
    
    return new_bool_wires, new_ternary_wires

