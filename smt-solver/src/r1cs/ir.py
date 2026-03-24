from __future__ import annotations

import subprocess
from pathlib import Path
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set
import json


# --------- SMT Result ---------
@dataclass
class SMTResult:
    satisfiable: bool
    model: Dict[str, int]

# --------- IR ---------

@dataclass(frozen=True)
class Variable:
    """
    A single R1CS variable (wire).
    Conventionally:
      - index 0 is the constant 1 wire
      - others are inputs/intermediates
    """
    index: int
    def is_constant_one(self) -> bool:
        return self.index == 0


@dataclass
class Term:
    """
    One term in a linear combination: coeff * variable
    """
    variable: Variable
    coeff: int


@dataclass
class LinearCombination:
    """
    Sum of terms:  Σ coeff_i * var_i
    """
    terms: List[Term]


@dataclass
class Constraint:
    """
    One R1CS constraint:  A * B = C
    """
    A: LinearCombination
    B: LinearCombination
    C: LinearCombination


@dataclass
class R1CS:
    """
    High-level R1CS representation.
    """
    n8: int
    prime: int
    nVars: int
    nOutputs: int
    nPubInputs: int
    nPrvInputs: int
    nLabels: int
    nConstraints: int
    useCustomGates: bool

    # Derived from `map` in the JSON
    variables: List[Variable]

    # Parsed constraints
    constraints: List[Constraint]
    
    # Wire indices that should be treated as boolean (0 or 1)
    bool_wire_indices: Set[int] = field(default_factory=set)
    
    # Wire indices that should be treated as ternary (p-1, 0, or 1)
    # Common pattern: when v1 = v2 + v3 where v1, v2 are boolean,
    # then v3 can only be -1, 0, or 1 (represented as p-1, 0, 1 in finite field)
    ternary_wire_indices: Set[int] = field(default_factory=set)

    # Hint values: wire_index -> constant value (from a known satisfying assignment)
    hints: Dict[int, int] = field(default_factory=dict)
