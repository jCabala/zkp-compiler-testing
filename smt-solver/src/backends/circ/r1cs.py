from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from src.r1cs.ir import Constraint, LinearCombination, R1CS, Term, Variable


_EXPORTER_DIR = Path(__file__).resolve().parent / "exporter"
_CIRC_DIR = Path(__file__).resolve().parents[3] / "third_party" / "circ"


def compile_zokrates_to_r1cs_json(zokrates_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{zokrates_path.stem}.circ.r1cs.json"
    proc = subprocess.run(
        [
            "cargo",
            "run",
            "--quiet",
            "--release",
            "--manifest-path",
            str(_EXPORTER_DIR / "Cargo.toml"),
            "--",
            str(zokrates_path),
            "--output",
            str(json_path),
        ],
        cwd=_CIRC_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"CirC export failed.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    if not json_path.exists():
        raise RuntimeError(f"Expected CirC export file not found at {json_path}")
    return json_path


def parse_circ_r1cs_json(json_path: Path) -> tuple[R1CS, dict[str, int], list[str], set[str]]:
    payload = json.loads(json_path.read_text())
    raw_r1cs = payload["r1cs"]

    raw_vars = raw_r1cs["vars"]
    raw_id_to_wire: dict[int, int] = {}
    name_to_wire: dict[str, int] = {}

    variables = [Variable(index=0)]
    for wire_idx, raw_var in enumerate(raw_vars, start=1):
        raw_id = int(raw_var)
        raw_id_to_wire[raw_id] = wire_idx
        name = _canonicalize_name(raw_r1cs["names"][str(raw_var)])
        name_to_wire[name] = wire_idx
        variables.append(Variable(index=wire_idx))

    constraints = [
        Constraint(
            A=_parse_lc(raw_constraint[0], raw_id_to_wire),
            B=_parse_lc(raw_constraint[1], raw_id_to_wire),
            C=_parse_lc(raw_constraint[2], raw_id_to_wire),
        )
        for raw_constraint in raw_r1cs["constraints"]
    ]

    input_names = [_canonicalize_name(name) for name in payload["input_names"]]
    input_names = [name for name in input_names if name != "return"]
    public_input_names = {_canonicalize_name(str(name)) for name in payload["public_input_names"]}
    public_input_names.discard("return")
    private_input_names = [name for name in input_names if name not in public_input_names]

    prime = _parse_prime(raw_r1cs["field"])
    r1cs = R1CS(
        n8=max(1, (prime.bit_length() + 7) // 8),
        prime=prime,
        nVars=len(variables),
        nOutputs=0,
        nPubInputs=len(public_input_names),
        nPrvInputs=len(private_input_names),
        nLabels=0,
        nConstraints=len(constraints),
        useCustomGates=False,
        variables=variables,
        constraints=constraints,
    )
    return r1cs, name_to_wire, input_names, public_input_names


def _parse_prime(raw_field) -> int:
    if raw_field == "FBls12381":
        return 52435875175126190479447740508185965837690552500527637822603658699938581184513
    if raw_field == "FBn254":
        return 21888242871839275222246405745257275088548364400416034343698204186575808495617
    if isinstance(raw_field, dict):
        if "IntField" in raw_field:
            return int(raw_field["IntField"][0])
        if "FBls12381" in raw_field:
            return 52435875175126190479447740508185965837690552500527637822603658699938581184513
        if "FBn254" in raw_field:
            return 21888242871839275222246405745257275088548364400416034343698204186575808495617
    raise ValueError(f"Unsupported Circ field encoding: {raw_field!r}")


def _parse_lc(raw_lc: dict, raw_id_to_wire: dict[int, int]) -> LinearCombination:
    terms: list[Term] = []
    constant = _parse_field_value(raw_lc["constant"])
    if constant != 0:
        terms.append(Term(variable=Variable(index=0), coeff=constant))

    for raw_var, raw_coeff in raw_lc["monomials"].items():
        coeff = _parse_field_value(raw_coeff)
        if coeff == 0:
            continue
        terms.append(
            Term(
                variable=Variable(index=raw_id_to_wire[int(raw_var)]),
                coeff=coeff,
            )
        )
    return LinearCombination(terms=terms)


def _parse_field_value(raw_value) -> int:
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, dict):
        if "i" in raw_value:
            return int(raw_value["i"])
        if "IntField" in raw_value:
            return int(raw_value["IntField"])
        if "FBls12381" in raw_value:
            return _limbs_to_int(raw_value["FBls12381"])
        if "FBn254" in raw_value:
            return _limbs_to_int(raw_value["FBn254"])
    raise ValueError(f"Unsupported Circ field value encoding: {raw_value!r}")


def _limbs_to_int(limbs) -> int:
    total = 0
    for idx, limb in enumerate(limbs):
        total |= int(limb) << (64 * idx)
    return total


def _canonicalize_name(name: str) -> str:
    return re.sub(r"_n\d+$", "", name)
