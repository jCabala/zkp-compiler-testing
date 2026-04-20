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


_NAME_MAP_PREFIX = "// SMT_SOLVER_NAME_MAP "


def _iter_expr_var_names(expr) -> set[str]:
	names: set[str] = set()
	match expr:
		case _ if expr is None:
			return names
		case _ if hasattr(expr, "name") and hasattr(expr, "variable_type") and not hasattr(expr, "op"):
			names.add(expr.name)
		case _ if hasattr(expr, "value") and hasattr(expr, "op"):
			names |= _iter_expr_var_names(expr.value)
		case _ if hasattr(expr, "lhs") and hasattr(expr, "rhs") and hasattr(expr, "op"):
			names |= _iter_expr_var_names(expr.lhs)
			names |= _iter_expr_var_names(expr.rhs)
		case _ if hasattr(expr, "condition") and hasattr(expr, "if_expr") and hasattr(expr, "else_expr"):
			names |= _iter_expr_var_names(expr.condition)
			names |= _iter_expr_var_names(expr.if_expr)
			names |= _iter_expr_var_names(expr.else_expr)
	return names


def _iter_stmt_var_names(stmt) -> set[str]:
	names: set[str] = set()
	if hasattr(stmt, "value"):
		names |= _iter_expr_var_names(stmt.value)
	if hasattr(stmt, "condition"):
		names |= _iter_expr_var_names(stmt.condition)
	if hasattr(stmt, "lhs"):
		names.add(stmt.lhs.name)
	if hasattr(stmt, "rhs"):
		names |= _iter_expr_var_names(stmt.rhs)
	return names


def _sanitize_identifier(name: str, used: set[str]) -> str:
	sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name)
	if not sanitized or not re.match(r"[A-Za-z][A-Za-z0-9_]*$", sanitized):
		sanitized = f"v_{sanitized.lstrip('_')}"
	if not sanitized:
		sanitized = "v"
	candidate = sanitized
	counter = 1
	while candidate in used:
		counter += 1
		candidate = f"{sanitized}_{counter}"
	used.add(candidate)
	return candidate


def _rename_expression(expr, name_map: dict[str, str]):
	match expr:
		case _ if expr is None:
			return expr
		case _ if hasattr(expr, "name") and hasattr(expr, "variable_type") and not hasattr(expr, "op"):
			renamed = expr.copy()
			renamed.name = name_map.get(expr.name, expr.name)
			if hasattr(expr, "fusion_expression") and expr.fusion_expression is not None:
				renamed.fusion_expression = _rename_expression(expr.fusion_expression, name_map)
			return renamed
		case _ if hasattr(expr, "value") and hasattr(expr, "op"):
			renamed = expr.copy()
			renamed.value = _rename_expression(expr.value, name_map)
			return renamed
		case _ if hasattr(expr, "lhs") and hasattr(expr, "rhs") and hasattr(expr, "op"):
			renamed = expr.copy()
			renamed.lhs = _rename_expression(expr.lhs, name_map)
			renamed.rhs = _rename_expression(expr.rhs, name_map)
			return renamed
		case _ if hasattr(expr, "condition") and hasattr(expr, "if_expr") and hasattr(expr, "else_expr"):
			renamed = expr.copy()
			renamed.condition = _rename_expression(expr.condition, name_map)
			renamed.if_expr = _rename_expression(expr.if_expr, name_map)
			renamed.else_expr = _rename_expression(expr.else_expr, name_map)
			return renamed
	return expr.copy() if hasattr(expr, "copy") else expr


def _rename_statement(stmt, name_map: dict[str, str]):
	renamed = stmt.copy()
	if hasattr(renamed, "value"):
		renamed.value = _rename_expression(renamed.value, name_map)
	if hasattr(renamed, "condition"):
		renamed.condition = _rename_expression(renamed.condition, name_map)
	if hasattr(renamed, "lhs"):
		renamed.lhs = _rename_expression(renamed.lhs, name_map)
	if hasattr(renamed, "rhs"):
		renamed.rhs = _rename_expression(renamed.rhs, name_map)
	return renamed


def _prepare_circuit_for_zokrates(circuit: Circuit) -> tuple[Circuit, dict[str, str]]:
	used_names: set[str] = {out.name for out in circuit.outputs}
	for stmt in circuit.statements:
		used_names |= _iter_stmt_var_names(stmt)

	filtered_inputs = [inp.copy() for inp in circuit.inputs if inp.name in used_names]
	prepared = Circuit(
		circuit.name,
		filtered_inputs,
		[out.copy() for out in circuit.outputs],
		[stmt.copy() for stmt in circuit.statements],
	)

	all_names = [var.name for var in prepared.inputs + prepared.outputs]
	name_map: dict[str, str] = {}
	used_sanitized: set[str] = set()
	for name in all_names:
		name_map[name] = _sanitize_identifier(name, used_sanitized)

	prepared.inputs = [_rename_expression(inp, name_map) for inp in prepared.inputs]
	prepared.outputs = [_rename_expression(out, name_map) for out in prepared.outputs]
	prepared.statements = [_rename_statement(stmt, name_map) for stmt in prepared.statements]
	return prepared, name_map


def _attach_name_map_comments(source: str, name_map: dict[str, str]) -> str:
	lines = [
		f"{_NAME_MAP_PREFIX}{sanitized} {original}"
		for original, sanitized in sorted(name_map.items())
		if original != sanitized
	]
	if not lines:
		return source
	return "\n".join(lines) + "\n" + source


def _parse_name_map_comments(source: str) -> dict[str, str]:
	parsed: dict[str, str] = {}
	for line in source.splitlines():
		if not line.startswith(_NAME_MAP_PREFIX):
			continue
		rest = line[len(_NAME_MAP_PREFIX):]
		parts = rest.split(" ", 1)
		if len(parts) == 2:
			parsed[parts[0]] = parts[1]
	return parsed


def smtlib2_to_zokrates(smtlib2: str, solver: str = "z3") -> tuple[str, list[str]]:
	"""Parse SMT-LIB v2 and convert it to ZoKrates code."""
	circuit_ir: Circuit = parse_smtlib2(smtlib2, solver=solver)
	bool_vars = [
		var.name for var in list(circuit_ir.inputs) + list(circuit_ir.outputs)
		if var.variable_type == VariableType.BOOLEAN
	]
	circuit_ir, name_map = _prepare_circuit_for_zokrates(circuit_ir)
	ir2zokrates_visitor = IR2ZokratesVisitor()
	zokrates_ast = ir2zokrates_visitor.visit_circuit(circuit_ir)
	emitter = ZokratesEmitter()
	return _attach_name_map_comments(emitter.emit(zokrates_ast), name_map), bool_vars


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
	renamed_to_original = _parse_name_map_comments(source)
	public_params = [name for name, is_private in params if not is_private]
	private_params = [name for name, is_private in params if is_private]

	name_to_wire: dict[str, int] = {}
	public_start = 1 + r1cs.nOutputs
	private_start = public_start + r1cs.nPubInputs

	for idx, name in enumerate(public_params):
		name_to_wire[renamed_to_original.get(name, name)] = public_start + idx
	for idx, name in enumerate(private_params):
		name_to_wire[renamed_to_original.get(name, name)] = private_start + idx
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
	renamed_to_original = _parse_name_map_comments(zokrates_path.read_text())
	name_to_wire = {renamed_to_original.get(name, name): idx for name, idx in name_to_wire.items()}
	input_names = [renamed_to_original.get(name, name) for name in input_names]
	public_input_names = {renamed_to_original.get(name, name) for name in public_input_names}
	bool_wire_indices, removable_wire_indices, _ = _resolve_wire_sets(name_to_wire, bool_vars)
	# Protect every non-removable wire, including unnamed CirC intermediates, so
	# that eliminate_wires never absorbs them and drops main-formula constraints.
	all_wire_indices = {v.index for v in r1cs.variables if v.index != 0}
	protected_wire_indices = all_wire_indices - removable_wire_indices
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
