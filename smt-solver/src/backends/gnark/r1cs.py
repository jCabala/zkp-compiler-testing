import re
import subprocess
import tempfile
from pathlib import Path
from typing import List

from src.r1cs.ir import R1CS, Variable, Constraint, LinearCombination, Term

# --------- Translation ---------

def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )

def get_r1cs_sr1cs(circuit_path: Path) -> str:
    """
    Runs the generated Go circuit and returns the produced .sr1cs text.

    The Go program is expected to be:
      go run <circuit_path> <outPath>

    and it writes sr1cs s-expressions to outPath.
    """
    circuit_name = circuit_path.stem
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        sr1cs_path = temp_dir_path / f"{circuit_name}.sr1cs"

        p = _run(["go", "run", str(circuit_path), str(sr1cs_path)])
        if p.returncode != 0:
            raise RuntimeError(f"Gnark compilation/dump failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

        if not sr1cs_path.exists():
            raise RuntimeError(f"Expected SR1CS file not found at {sr1cs_path}")

        return sr1cs_path.read_text(encoding="utf-8")


# --------- Parsing ---------

BN254_FR_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617

class GNARKFieldPrimes:
    BN254 = BN254_FR_PRIME
    U32_2013265921 = 2013265921
    U32_2130706433 = 2130706433
    U32_47 = 47
    # Add more as needed


_RE_PRIME = re.compile(r"^\s*\(prime-number\s+([0-9]+)\s*\)\s*$")
_RE_IN = re.compile(r"^\s*\(in\s+([0-9]+)\s*\)\s*$")
_RE_OUT = re.compile(r"^\s*\(out\s+([0-9]+)\s*\)\s*$")
_RE_LABEL = re.compile(r"^\s*\(label\s+([0-9]+)\s+(.+?)\s*\)\s*$")
_RE_EXTRA = re.compile(r"^\s*\(extra-constraint\s+(.+?)\s*\)\s*$")

# (constraint [ ... ] [ ... ] [ ... ])
_RE_CONSTRAINT_LINE = re.compile(r"^\s*\(constraint\s+(.*)\)\s*$")
_RE_BRACKET_GROUPS = re.compile(r"\[(.*?)\]")
_RE_PAIR = re.compile(r"\(\s*([^\s\)]+)\s+([0-9]+)\s*\)")


def parse_sr1cs(sr1cs_str: str) -> R1CS:
    """
    Parses sr1cs s-expressions like:

      (prime-number 47)
      (in 3)
      (out 9)
      (label 3 x)
      (extra-constraint ...)
      (constraint [(c1 0) (c3 5)] [(c1 2)] [(c1 7)])

    into the R1CS IR (constraints only), while using (in)/(out) to fill counts.

    Notes:
      - Labels / extra-constraints are currently parsed but not stored in R1CS IR
        (your src.r1cs.ir types don't expose a place for them yet).
      - Coefficients are reduced mod prime.
      - nVars inferred as max VID + 1.
    """
    prime: int | None = None
    in_vars: list[int] = []
    out_vars: list[int] = []
    labels: dict[int, str] = {}
    extra_constraints: list[str] = []

    constraints: List[Constraint] = []
    max_var = 0

    for raw_line in sr1cs_str.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = _RE_PRIME.match(line)
        if m:
            prime = int(m.group(1))
            continue

        m = _RE_IN.match(line)
        if m:
            in_vars.append(int(m.group(1)))
            continue

        m = _RE_OUT.match(line)
        if m:
            out_vars.append(int(m.group(1)))
            continue

        m = _RE_LABEL.match(line)
        if m:
            vid = int(m.group(1))
            # label name might be quoted or not; keep raw token(s)
            name = m.group(2).strip()
            # strip surrounding quotes if present
            if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
                name = name[1:-1]
            labels[vid] = name
            continue

        m = _RE_EXTRA.match(line)
        if m:
            extra_constraints.append(m.group(1).strip())
            continue

        m = _RE_CONSTRAINT_LINE.match(line)
        if m:
            if prime is None:
                raise ValueError("Encountered (constraint ...) before (prime-number ...).")
            payload = m.group(1)

            groups = _RE_BRACKET_GROUPS.findall(payload)
            if len(groups) != 3:
                raise ValueError(f"Malformed constraint line (expected 3 [..] groups): {raw_line}")

            A = _parse_lc_from_group(groups[0], prime=prime)
            B = _parse_lc_from_group(groups[1], prime=prime)
            C = _parse_lc_from_group(groups[2], prime=prime)
            constraints.append(Constraint(A=A, B=B, C=C))

            for lc in (A, B, C):
                for term in lc.terms:
                    if term.variable.index > max_var:
                        max_var = term.variable.index
            continue

        # If you want strict parsing, raise here. Otherwise, ignore unknown lines.
        # raise ValueError(f"Unrecognized sr1cs line: {raw_line!r}")

    if prime is None:
        raise ValueError("Missing (prime-number ...) header in sr1cs.")

    nVars = max_var + 1 if constraints else 0
    variables = [Variable(i) for i in range(nVars)]

    # Populate counts using annotations
    # (Your IR doesn't distinguish public/private inputs yet; treat all (in ...) as private inputs.)
    nPrvInputs = len(in_vars)
    nOutputs = len(out_vars)

    return R1CS(
        n8=0,  # unknown from sr1cs
        prime=prime,
        nVars=nVars,
        nOutputs=nOutputs,
        nPubInputs=0,
        nPrvInputs=nPrvInputs,
        nLabels=nVars,  # conservative default
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
      - compact string e.g. "c0", "c1", "c42" (treated as decimal after 'c')
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
        return int(s[1:], 10)

    return int(s, 10)


def _parse_lc_from_group(group: str, *, prime: int) -> LinearCombination:
    """
    Parses a bracket-group payload like:
      "(c1 0) (c3 5) (12 9)"
    into LinearCombination.
    """
    terms: List[Term] = []
    for coeff_s, var_s in _RE_PAIR.findall(group):
        var_idx = int(var_s)
        coeff = _parse_coeff(coeff_s) % prime
        if coeff != 0:
            terms.append(Term(variable=Variable(var_idx), coeff=coeff))
    return LinearCombination(terms=terms)
