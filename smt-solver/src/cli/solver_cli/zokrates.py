import re
import tempfile
from pathlib import Path
from random import random

from src.backends.circ.r1cs import compile_zokrates_to_r1cs_json, parse_circ_r1cs_json
from src.backends.zokrates.emitter import EmitVisitor as ZokratesEmitter
from src.backends.zokrates.ir2zokrates import IR2ZokratesVisitor
from src.backends.zokrates.r1cs import compile_to_r1cs, parse_r1cs
from src.cli.solver_cli.adaptive_hints import HINT_PROBABILITY
from src.cli.solver_cli.common import log, run_picus, solution_to_str
from src.r1cs.dump import dump_r1cs as dump_r1cs_text
from src.r1cs.optimization.eliminate import eliminate_wires
from src.r1cs.optimization.optimize import optimize_r1cs
from src.r1cs.sr1cs import dump_sr1cs
from src.r1cs.solve import solve_r1cs
from src.smt_lib.smt_lib_parser import parse_smtlib2
from src.smt_lib.zk_ir import Circuit, VariableType


def smtlib2_to_zokrates(smtlib2: str, solver: str = "z3") -> tuple[str, list[str]]:
	"""Parse SMT-LIB v2 and convert it to ZoKrates code."""
	circuit_ir: Circuit = parse_smtlib2(smtlib2, solver=solver)
	bool_vars = [
		var.name for var in list(circuit_ir.inputs) + list(circuit_ir.outputs)
		if var.variable_type == VariableType.BOOLEAN
	]
	ir2zokrates_visitor = IR2ZokratesVisitor()
	zokrates_ast = ir2zokrates_visitor.visit_circuit(circuit_ir)
	emitter = ZokratesEmitter()
	return emitter.emit(zokrates_ast), bool_vars


def _parse_main_params(source: str) -> list[tuple[str, bool]]:
	match = re.search(r"def\s+main\(([^)]*)\)", source)
	if not match:
		return []

	params = []
	for raw_param in match.group(1).split(","):
		param = raw_param.strip()
		if not param:
			continue
		parts = param.split()
		is_private = parts[0] == "private"
		name = parts[-1]
		params.append((name, is_private))
	return params


def _build_name_to_wire_map(source: str, r1cs) -> dict[str, int]:
	params = _parse_main_params(source)
	public_params = [name for name, is_private in params if not is_private]
	private_params = [name for name, is_private in params if is_private]

	name_to_wire: dict[str, int] = {}
	public_start = 1 + r1cs.nOutputs
	private_start = public_start + r1cs.nPubInputs

	for idx, name in enumerate(public_params):
		name_to_wire[name] = public_start + idx
	for idx, name in enumerate(private_params):
		name_to_wire[name] = private_start + idx
	return name_to_wire


def _resolve_hints_from_name_map(name_to_wire: dict[str, int], hint_model: dict) -> dict[int, int]:
	hints: dict[int, int] = {}
	for var_name, value in hint_model.items():
		if var_name in name_to_wire:
			hints[name_to_wire[var_name]] = int(value) if isinstance(value, bool) else value
	return hints


def resolve_hints_for_zokrates(source: str, r1cs, hint_model: dict) -> dict[int, int]:
	return _resolve_hints_from_name_map(_build_name_to_wire_map(source, r1cs), hint_model)


def _resolve_wire_sets(name_to_wire: dict[str, int], bool_vars: tuple[str, ...]) -> tuple[set[int], set[int], set[int]]:
	bool_wire_indices = {name_to_wire[name] for name in bool_vars if name in name_to_wire}
	removable_wire_indices = {
		wire_idx for name, wire_idx in name_to_wire.items()
		if name.startswith("_removable_")
	}
	protected_wire_indices = {
		wire_idx for name, wire_idx in name_to_wire.items()
		if not name.startswith("_removable_")
	}
	return bool_wire_indices, removable_wire_indices, protected_wire_indices


def _resolve_picus_io_from_names(name_to_wire: dict[str, int], input_names: list[str], public_input_names: set[str]) -> tuple[list[int], list[int]]:
	input_wires: list[int] = []
	output_wires: list[int] = []

	for name in input_names:
		wire_idx = name_to_wire.get(name)
		if wire_idx is None:
			continue
		if name in public_input_names:
			output_wires.append(wire_idx)
		else:
			input_wires.append(wire_idx)

	return input_wires, output_wires


def _make_circ_compatible_source(source: str) -> str:
	"""Lower our modern brace-style ZoKrates subset into the older syntax Circ accepts."""
	lines = source.splitlines()
	out: list[str] = []
	indent = 0
	added_dummy_return = False

	for raw_line in lines:
		stripped = raw_line.strip()
		if not stripped:
			continue

		while stripped.startswith("}"):
			indent = max(indent - 4, 0)
			stripped = stripped[1:].strip()
			if not stripped:
				break
		if not stripped:
			continue

		if stripped.startswith("def main(") and stripped.endswith("{"):
			header = stripped[:-1].rstrip()
			if "->" not in header:
				header += " -> bool"
				added_dummy_return = True
			stripped = header + ":"
			out.append(" " * indent + stripped)
			indent += 4
			continue

		if stripped.startswith("for ") and stripped.endswith("{"):
			stripped = stripped[:-1].rstrip() + ":"
			out.append(" " * indent + stripped)
			indent += 4
			continue

		if stripped == "return;" and added_dummy_return:
			stripped = "return true"
		elif stripped.endswith(";"):
			stripped = stripped[:-1]

		out.append(" " * indent + stripped)

	return "\n".join(out) + "\n"


def build_r1cs_from_zokrates(
	zokrates_path: Path,
	r1cs_path: Path,
	*,
	bool_vars: tuple[str, ...],
	with_logs: bool,
	eliminate_removable: bool = True,
	optimize: bool = True,
):
	"""Parse ZoKrates R1CS and apply the same cleanup passes as other backends."""
	source = zokrates_path.read_text()
	r1cs = parse_r1cs(r1cs_path)
	name_to_wire = _build_name_to_wire_map(source, r1cs)
	bool_wire_indices, removable_wire_indices, protected_wire_indices = _resolve_wire_sets(name_to_wire, bool_vars)
	r1cs.bool_wire_indices = bool_wire_indices

	if eliminate_removable and removable_wire_indices:
		before = r1cs.nConstraints
		r1cs = eliminate_wires(r1cs, removable_wire_indices, protected_wire_indices)
		log(
			f"Eliminated {before - r1cs.nConstraints} removable constraints ({r1cs.nConstraints} remaining)",
			with_logs,
		)

	if optimize:
		log("Optimizing R1CS...", with_logs)
		r1cs = optimize_r1cs(r1cs, with_logs=with_logs)
	return r1cs, name_to_wire


def build_r1cs_from_circ(
	zokrates_path: Path,
	*,
	bool_vars: tuple[str, ...],
	with_logs: bool,
	workdir: Path,
	eliminate_removable: bool = True,
	optimize: bool = True,
):
	"""Compile ZoKrates source through Circ and normalize it into the internal R1CS."""
	circ_source_path = workdir / f"{zokrates_path.stem}.circ.zok"
	circ_source_path.write_text(_make_circ_compatible_source(zokrates_path.read_text()))
	json_path = compile_zokrates_to_r1cs_json(circ_source_path, workdir)
	r1cs, name_to_wire, input_names, public_input_names = parse_circ_r1cs_json(json_path)
	bool_wire_indices, removable_wire_indices, protected_wire_indices = _resolve_wire_sets(name_to_wire, bool_vars)
	r1cs.bool_wire_indices = bool_wire_indices

	if eliminate_removable and removable_wire_indices:
		before = r1cs.nConstraints
		r1cs = eliminate_wires(r1cs, removable_wire_indices, protected_wire_indices)
		log(
			f"Eliminated {before - r1cs.nConstraints} removable constraints ({r1cs.nConstraints} remaining)",
			with_logs,
		)

	if optimize:
		log("Optimizing R1CS...", with_logs)
		r1cs = optimize_r1cs(r1cs, with_logs=with_logs)

	return r1cs, name_to_wire, input_names, public_input_names


def solve_zokrates(
	zokrates_path: Path,
	*,
	bool_vars: tuple[str, ...],
	with_model: bool,
	with_logs: bool,
	solver: str,
	tmp_dir: Path,
	hint_model: dict | None = None,
	solving_timeout: int | None = None,
	hint_probability: float = HINT_PROBABILITY,
	compiler: str = "zokrates",
	dump_r1cs: Path | None = None,
	with_circ: bool = False,
) -> str:
	"""Compile ZoKrates source to R1CS and solve through the standard backend pipeline."""
	del with_model
	source = zokrates_path.read_text()

	tmp_dir.mkdir(parents=True, exist_ok=True)
	with tempfile.TemporaryDirectory(dir=tmp_dir) as temp_dir:
		workdir = Path(temp_dir)
		source_path = workdir / zokrates_path.name
		source_path.write_text(source)

		log(f"Compiling ZoKrates file: {source_path}...", with_logs)
		if with_circ:
			log("Compiling ZoKrates through Circ...", with_logs)
			r1cs, name_to_wire, input_names, public_input_names = build_r1cs_from_circ(
				source_path,
				bool_vars=bool_vars,
				with_logs=with_logs,
				workdir=workdir,
				eliminate_removable=True,
				optimize=True,
			)
		else:
			try:
				r1cs_path = compile_to_r1cs(source_path, workdir, compiler=compiler)
			except RuntimeError as exc:
				error_text = str(exc)
				if "Assertion failed" in error_text:
					log("ZoKrates rejected the program during compilation with an assertion failure", with_logs)
					return "unsat"
				if solver == "picus" and "unconstrained variable" in error_text:
					log("ZoKrates rejected the program as underconstrained during compilation", with_logs)
					return "unsat"
				raise

			r1cs, name_to_wire = build_r1cs_from_zokrates(
				source_path,
				r1cs_path,
				bool_vars=bool_vars,
				with_logs=with_logs,
				eliminate_removable=True,
				optimize=True,
			)
			params = _parse_main_params(source)
			input_names = [name for name, _ in params]
			public_input_names = {name for name, is_private in params if not is_private}

		wire_hints = {}
		if hint_model:
			wire_hints = _resolve_hints_from_name_map(name_to_wire, hint_model)
			wire_hints = {k: v for k, v in wire_hints.items() if random() < hint_probability}
			log(
				f"Resolved {len(wire_hints)} hint wire assignments (after probabilistic filtering)",
				with_logs,
			)

		if dump_r1cs is not None:
			to_dump = r1cs
			if wire_hints:
				to_dump.hints = wire_hints
			dump_r1cs.write_text(dump_r1cs_text(to_dump))

		if solver == "picus":
			log("Solving R1CS using Picus...", with_logs)
			input_wires, output_wires = _resolve_picus_io_from_names(name_to_wire, input_names, public_input_names)
			sr1cs_path = workdir / f"{zokrates_path.stem}.sr1cs"
			sr1cs_path.write_text(
				dump_sr1cs(
					r1cs,
					input_wires=input_wires,
					output_wires=output_wires,
				)
			)
			return run_picus(sr1cs_path, hints=wire_hints or None, solving_timeout=solving_timeout)

		if wire_hints:
			r1cs.hints = wire_hints

		log("Solving R1CS using a SMT solver...", with_logs)
		solution = solve_r1cs(r1cs, backend=solver, with_logs=with_logs, solving_timeout=solving_timeout)
		return solution_to_str(solution)
