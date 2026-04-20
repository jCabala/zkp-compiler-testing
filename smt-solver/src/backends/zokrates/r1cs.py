from __future__ import annotations

import struct
import subprocess
from pathlib import Path

from src.r1cs.ir import R1CS, Constraint, LinearCombination, Term, Variable


_MAGIC = b"r1cs"
_SECTION_HEADER = 1
_SECTION_CONSTRAINTS = 2
_SECTION_WIRE_MAP = 3


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		cmd,
		cwd=str(cwd) if cwd is not None else None,
		text=True,
		capture_output=True,
		check=False,
	)


def compile_to_r1cs(zokrates_path: Path, out_dir: Path, compiler: str = "zokrates") -> Path:
	"""Compile a .zok file to a .r1cs binary in out_dir and return the path."""
	out_dir.mkdir(parents=True, exist_ok=True)
	binary_path = out_dir / zokrates_path.stem
	r1cs_path = out_dir / f"{zokrates_path.stem}.r1cs"
	proc = _run(
		[
			compiler,
			"compile",
			"-i",
			str(zokrates_path),
			"-o",
			str(binary_path),
			"-r",
			str(r1cs_path),
			"--curve",
			"bn128",
		]
	)
	if proc.returncode != 0:
		raise RuntimeError(f"ZoKrates compilation failed.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
	if not r1cs_path.exists():
		raise RuntimeError(f"Expected R1CS file not found at {r1cs_path}")
	return r1cs_path


def parse_r1cs(r1cs_path: Path) -> R1CS:
	"""Parse a ZoKrates-generated binary .r1cs file into the internal R1CS IR."""
	data = r1cs_path.read_bytes()
	if len(data) < 12:
		raise ValueError("Invalid R1CS file: too short")
	if data[:4] != _MAGIC:
		raise ValueError(f"Invalid R1CS magic: {data[:4]!r}")

	version = struct.unpack_from("<I", data, 4)[0]
	if version != 1:
		raise ValueError(f"Unsupported R1CS version: {version}")

	n_sections = struct.unpack_from("<I", data, 8)[0]
	offset = 12
	sections: dict[int, bytes] = {}
	for _ in range(n_sections):
		section_type = struct.unpack_from("<I", data, offset)[0]
		offset += 4
		section_len = struct.unpack_from("<Q", data, offset)[0]
		offset += 8
		sections[section_type] = data[offset:offset + section_len]
		offset += section_len

	header = sections.get(_SECTION_HEADER)
	constraints_blob = sections.get(_SECTION_CONSTRAINTS)
	wire_map_blob = sections.get(_SECTION_WIRE_MAP)
	if header is None or constraints_blob is None:
		raise ValueError("Missing required sections in ZoKrates R1CS file")

	field_size = struct.unpack_from("<I", header, 0)[0]
	cursor = 4
	prime = int.from_bytes(header[cursor:cursor + field_size], "little")
	cursor += field_size
	n_vars = struct.unpack_from("<I", header, cursor)[0]
	cursor += 4
	n_outputs = struct.unpack_from("<I", header, cursor)[0]
	cursor += 4
	n_pub_inputs = struct.unpack_from("<I", header, cursor)[0]
	cursor += 4
	n_prv_inputs = struct.unpack_from("<I", header, cursor)[0]
	cursor += 4
	n_labels = struct.unpack_from("<Q", header, cursor)[0]
	cursor += 8
	n_constraints = struct.unpack_from("<I", header, cursor)[0]
	cursor += 4

	if wire_map_blob is not None:
		map_entries = [
			struct.unpack_from("<Q", wire_map_blob, i)[0]
			for i in range(0, len(wire_map_blob), 8)
		]
	else:
		map_entries = list(range(n_vars))
	variables = [Variable(index=int(idx)) for idx in map_entries]

	constraints: list[Constraint] = []
	cursor = 0
	for _ in range(n_constraints):
		A, cursor = _parse_linear_combination(constraints_blob, cursor, field_size, prime, variables)
		B, cursor = _parse_linear_combination(constraints_blob, cursor, field_size, prime, variables)
		C, cursor = _parse_linear_combination(constraints_blob, cursor, field_size, prime, variables)
		constraints.append(Constraint(A=A, B=B, C=C))

	return R1CS(
		n8=field_size,
		prime=prime,
		nVars=n_vars,
		nOutputs=n_outputs,
		nPubInputs=n_pub_inputs,
		nPrvInputs=n_prv_inputs,
		nLabels=int(n_labels),
		nConstraints=n_constraints,
		useCustomGates=False,
		variables=variables,
		constraints=constraints,
	)


def _parse_linear_combination(
	data: bytes,
	offset: int,
	field_size: int,
	prime: int,
	variables: list[Variable],
) -> tuple[LinearCombination, int]:
	n_terms = struct.unpack_from("<I", data, offset)[0]
	offset += 4
	terms: list[Term] = []
	for _ in range(n_terms):
		wire_idx = struct.unpack_from("<I", data, offset)[0]
		offset += 4
		coeff = int.from_bytes(data[offset:offset + field_size], "little") % prime
		offset += field_size
		if coeff == 0:
			continue
		terms.append(Term(variable=variables[wire_idx], coeff=coeff))
	return LinearCombination(terms=terms), offset
