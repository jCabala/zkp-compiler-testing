import subprocess
from pathlib import Path
import tempfile
from typing import Dict, List, Any, Tuple, Set
import json
from src.r1cs.ir import R1CS, Variable, Constraint, LinearCombination, Term
from src.backends.circom.sym_parser import resolve_bool_wires

# --------- Translation ---------

def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    # text=True => strings, not bytes
    # capture_output=True => no console spam
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )

class OptFlag(str):
    O0 = "--O0"
    O1 = "--O1"
    O2 = "--O2"

def get_r1cs_json(circuit_path: Path, opt_flag: OptFlag = OptFlag.O0) -> str:
    temp_dir_path = Path(tempfile.mkdtemp())
    circuit_name = circuit_path.stem

    # Compile
    p = _run(["circom", str(circuit_path), "--r1cs", opt_flag, "-o", str(temp_dir_path)])
    if p.returncode != 0:
        raise RuntimeError(f"Circom compilation failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

    r1cs_path = temp_dir_path / f"{circuit_name}.r1cs"
    if not r1cs_path.exists():
        raise RuntimeError(f"Expected R1CS file not found at {r1cs_path}")

    # Convert
    r1cs_json_path = temp_dir_path / f"{circuit_name}.json"
    p = _run(["snarkjs", "r1cs", "export", "json", str(r1cs_path), str(r1cs_json_path)])
    if p.returncode != 0:
        raise RuntimeError(f"snarkjs conversion failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

    return r1cs_json_path.read_text()


def get_r1cs_with_sym(circuit_path: Path, opt_flag: OptFlag = OptFlag.O0, bool_signal_names: List[str] = None) -> Tuple[str, Set[int]]:
    """
    Compile a Circom circuit to R1CS with symbol information.
    
    Args:
        circuit_path: Path to the .circom file
        opt_flag: Optimization flag for circom compiler
        bool_signal_names: List of signal names to treat as boolean (e.g., ["main.flag", "main.arr[0]"])
        
    Returns:
        Tuple of (r1cs_json_string, bool_wire_indices)
    """
    temp_dir_path = Path(tempfile.mkdtemp())
    circuit_name = circuit_path.stem

    # Compile with --sym flag
    p = _run(["circom", str(circuit_path), "--r1cs", "--sym", opt_flag, "-o", str(temp_dir_path)])
    if p.returncode != 0:
        raise RuntimeError(f"Circom compilation failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

    r1cs_path = temp_dir_path / f"{circuit_name}.r1cs"
    sym_path = temp_dir_path / f"{circuit_name}.sym"
    
    if not r1cs_path.exists():
        raise RuntimeError(f"Expected R1CS file not found at {r1cs_path}")
    if not sym_path.exists():
        raise RuntimeError(f"Expected .sym file not found at {sym_path}")

    # Convert R1CS to JSON
    r1cs_json_path = temp_dir_path / f"{circuit_name}.json"
    p = _run(["snarkjs", "r1cs", "export", "json", str(r1cs_path), str(r1cs_json_path)])
    if p.returncode != 0:
        raise RuntimeError(f"snarkjs conversion failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

    r1cs_json_str = r1cs_json_path.read_text()
    
    # Resolve boolean wire indices
    bool_wire_indices: Set[int] = set()
    if bool_signal_names:
        bool_wire_indices = resolve_bool_wires(sym_path, bool_signal_names)
    
    return r1cs_json_str, bool_wire_indices


def parse_r1cs_json(json_str: str, bool_wire_indices: Set[int] = None) -> R1CS:
    """
    Parse the given JSON string into an R1CS dataclass structure.
    
    Args:
        json_str: JSON string representation of R1CS
        bool_wire_indices: Optional set of wire indices to treat as boolean
    """
    data = json.loads(json_str)

    # Build Variable objects from the `map` array
    # e.g. "map": [0, 1, 2, 3]  ->  Variable(0), Variable(1), ...
    map_indices = [int(x) for x in data["map"]]
    variables_list = [Variable(index=i) for i in map_indices]

    # Parse constraints: [[[A], [B], [C]], ...]
    constraints: List[Constraint] = []
    for raw_constraint in data["constraints"]:
        if len(raw_constraint) != 3:
            raise ValueError(
                f"Expected 3 linear combinations per constraint, got {len(raw_constraint)}"
            )

        A_obj, B_obj, C_obj = raw_constraint
        A = _parse_linear_comb(A_obj, variables_list)
        B = _parse_linear_comb(B_obj, variables_list)
        C = _parse_linear_comb(C_obj, variables_list)

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
        variables=variables_list,
        constraints=constraints,
        bool_wire_indices=bool_wire_indices or set(),
    )

    return r1cs


def _parse_linear_comb(
    obj: Dict[str, Any],
    variables_list: List[Variable],
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
        if var_idx >= len(variables_list):
            raise ValueError(f"Variable index {var_idx} not found in map/variables")
        variable = variables_list[var_idx]
        terms.append(Term(variable=variable, coeff=coeff))

    return LinearCombination(terms=terms)
