from __future__ import annotations

import subprocess
from pathlib import Path
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Any
import json


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
