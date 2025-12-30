from __future__ import annotations

import os
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


# --------- Translation ---------

def get_r1cs_json(circuit_path: Path) -> str:
    """
    Use circom compiler to get .r1cs file and then use snarkjs to convert it to .json format.
    """

    # Create a temporary directory for output
    temp_dir = tempfile.mkdtemp()
    temp_dir_path = Path(temp_dir)

    # Get the circuit name without extension
    circuit_name = circuit_path.stem

    # Compile the circuit to get the .r1cs file
    compile_command = f"circom {circuit_path} --r1cs -o {temp_dir}"
    compile_result = os.system(compile_command)

    if compile_result != 0:
        raise RuntimeError("Circom compilation failed.")

    # The .r1cs file will be in temp_dir with the circuit name
    r1cs_path = temp_dir_path / f"{circuit_name}.r1cs"

    if not r1cs_path.exists():
        raise RuntimeError(f"Expected R1CS file not found at {r1cs_path}")

    # Convert the .r1cs file to .json format using snarkjs
    r1cs_json_path = temp_dir_path / f"{circuit_name}.json"
    convert_command = f"snarkjs r1cs export json {r1cs_path} {r1cs_json_path}"
    convert_result = os.system(convert_command)

    if convert_result != 0:
        raise RuntimeError("snarkjs conversion failed.")

    # Read the .json file content
    with open(r1cs_json_path, "r") as json_file:
        r1cs_json_content = json_file.read()

    return r1cs_json_content


def parse_r1cs_json(json_str: str) -> R1CS:
    """
    Parse the given JSON string into an R1CS dataclass structure.
    """
    data = json.loads(json_str)

    # Build Variable objects from the `map` array
    # e.g. "map": [0, 1, 2, 3]  ->  Variable(0), Variable(1), ...
    map_indices = [int(x) for x in data["map"]]
    variables = [Variable(index=i) for i in map_indices]
    variables_by_index: Dict[int, Variable] = {v.index: v for v in variables}

    # Parse constraints: [[[A], [B], [C]], ...]
    constraints: List[Constraint] = []
    for raw_constraint in data["constraints"]:
        if len(raw_constraint) != 3:
            raise ValueError(
                f"Expected 3 linear combinations per constraint, got {len(raw_constraint)}"
            )

        A_obj, B_obj, C_obj = raw_constraint
        A = _parse_linear_comb(A_obj, variables_by_index)
        B = _parse_linear_comb(B_obj, variables_by_index)
        C = _parse_linear_comb(C_obj, variables_by_index)

        constraints.append(Constraint(A=A, B=B, C=C))

    r1cs = R1CS(
        n8=int(data["n8"]),
        prime=int(data["prime"]) if isinstance(data["prime"], str) else int(data["prime"]),
        nVars=int(data["nVars"]),
        nOutputs=int(data["nOutputs"]),
        nPubInputs=int(data["nPubInputs"]),
        nPrvInputs=int(data["nPrvInputs"]),
        nLabels=int(data["nLabels"]),
        nConstraints=int(data["nConstraints"]),
        useCustomGates=bool(data["useCustomGates"]),
        variables=variables,
        constraints=constraints,
    )

    return r1cs


def _parse_linear_comb(
    obj: Dict[str, Any],
    variables_by_index: Dict[int, Variable],
) -> LinearCombination:
    """
    Convert a JSON object like { "2": "123", "3": "1" } into
    LinearCombination(
        terms=[
            Term(variable=Variable(index=2), coeff=123),
            Term(variable=Variable(index=3), coeff=1),
        ]
    )
    """
    terms: List[Term] = []
    for k, v in obj.items():
        var_idx = int(k)
        coeff = int(v) if isinstance(v, str) else int(v)
        if var_idx not in variables_by_index:
            raise ValueError(f"Variable index {var_idx} not found in map/variables")
        variable = variables_by_index[var_idx]
        terms.append(Term(variable=variable, coeff=coeff))

    return LinearCombination(terms=terms)
