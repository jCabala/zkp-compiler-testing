import subprocess
from pathlib import Path
import tempfile
from typing import Dict, List, Any
import json
from src.r1cs.ir import R1CS, Variable, Constraint, LinearCombination, Term

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

def get_r1cs_json(circuit_path: Path) -> str:
    circuit_name = circuit_path.stem
    temp_dir_path = Path(tempfile.mkdtemp())
    r1cs_json_path = temp_dir_path / f"{circuit_name}.json"

    # Compile
    p = _run(["go",  "run", str(circuit_path), str(r1cs_json_path)])
    if p.returncode != 0:
        raise RuntimeError(f"Circom compilation failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

    if not r1cs_json_path.exists():
        raise RuntimeError(f"Expected R1CS file not found at {r1cs_path}")

    # Convert
    return r1cs_json_path.read_text()


# --------- Parsing ---------

_BN254_FR_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617

_FIELD_PRIMES = {
    "BN254": _BN254_FR_PRIME,
    # add more if you need:
    # "BLS12_381": <prime>,
}

def parse_r1cs_json(json_str: str) -> R1CS:
    """
    Parses JSON like:

    {
      "field": "BN254",
      "system": "R1CS",
      "constraints": [
        {"id":0, "L":[{"var":1,"coeff":"c1"}], "R":[...], "O":[...]}
      ]
    }

    into the IR defined above.

    Notes:
      - This JSON does not provide counts like nOutputs/nPubInputs/etc,
        so those are set to 0 (except nVars/nConstraints which are inferred).
      - Coefficients are reduced mod the field prime.
    """
    obj = json.loads(json_str)
    if not isinstance(obj, dict):
        raise TypeError("Top-level JSON must be an object")

    field = obj.get("field")
    if not isinstance(field, str) or not field:
        raise ValueError("Missing/invalid 'field'")

    prime = _FIELD_PRIMES.get(field)
    if prime is None:
        raise ValueError(f"Unsupported field {field!r}. Known: {sorted(_FIELD_PRIMES)}")

    system = obj.get("system")
    if system != "R1CS":
        raise ValueError(f"Expected system='R1CS', got {system!r}")

    constraints_json = obj.get("constraints", [])
    if not isinstance(constraints_json, list):
        raise TypeError("Expected 'constraints' to be a list")

    constraints: List[Constraint] = []
    max_var = 0  # infer nVars as max var index + 1 (including constant wire 0)
    for c in constraints_json:
        if not isinstance(c, dict):
            raise TypeError(f"Constraint must be object, got {type(c)}")

        A = _parse_lc(c.get("L", []), prime=prime)
        B = _parse_lc(c.get("R", []), prime=prime)
        C = _parse_lc(c.get("O", []), prime=prime)
        constraints.append(Constraint(A=A, B=B, C=C))

        for lc in (A, B, C):
            for term in lc.terms:
                if term.variable.index > max_var:
                    max_var = term.variable.index

    nVars = max_var + 1  # includes var 0 if it appears; still correct if absent
    variables = [Variable(i) for i in range(nVars)]

    return R1CS(
        n8=0,  # unknown from this JSON format
        prime=prime,
        nVars=nVars,
        nOutputs=0,
        nPubInputs=0,
        nPrvInputs=0,
        nLabels=nVars,  # reasonable default if you don't have a separate label map
        nConstraints=len(constraints),
        useCustomGates=False,
        variables=variables,
        constraints=constraints,
    )

def _parse_coeff(value: object) -> int:
    """
    Accepts:
      - int
      - decimal string e.g. "123"
      - hex string e.g. "0x2a"
      - compact string e.g. "c0", "c1", "c42"  (treated as decimal after 'c')
    """
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Unsupported coeff type: {type(value)} (value={value!r})")

    s = value.strip()
    if not s:
        raise ValueError("Empty coeff string")

    if s.startswith(("0x", "0X")):
        return int(s, 16)

    if s.startswith("c") and len(s) > 1:
        # Your sample uses "c1", "c3", etc.
        # Interpreted here as decimal integers 1, 3, ...
        return int(s[1:], 10)

    # fallback: decimal
    return int(s, 10)


def _parse_lc(lc_terms: object, *, prime: int) -> LinearCombination:
    if lc_terms is None:
        return LinearCombination(terms=[])
    if not isinstance(lc_terms, list):
        raise TypeError(f"Expected list for LC, got {type(lc_terms)}")

    terms: List[Term] = []
    for t in lc_terms:
        if not isinstance(t, dict):
            raise TypeError(f"Expected dict term, got {type(t)}")
        if "var" not in t or "coeff" not in t:
            raise ValueError(f"Term missing 'var'/'coeff': {t!r}")

        var_idx = t["var"]
        if not isinstance(var_idx, int) or var_idx < 0:
            raise ValueError(f"Invalid var index: {var_idx!r}")

        coeff = _parse_coeff(t["coeff"]) % prime
        # You may choose to drop zero-coeff terms:
        if coeff != 0:
            terms.append(Term(variable=Variable(var_idx), coeff=coeff))

    return LinearCombination(terms=terms)