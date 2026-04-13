from pathlib import Path
from random import Random, random
from src.cli.solver_cli.adaptive_hints import HINT_PROBABILITY
from src.smt_lib.smt_lib_parser import parse_smtlib2
from src.smt_lib.zk_ir import Circuit
from src.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from src.backends.circom.emitter import EmitVisitor as CircomEmitter
from src.r1cs.solve import solve_r1cs
from src.r1cs.optimization.optimize import optimize_r1cs
from src.r1cs.optimization.eliminate import eliminate_wires
from src.cli.solver_cli.common import log, solution_to_str, run_picus


def smtlib2_to_circom(smtlib2: str, solver: str = "z3") -> tuple[str, list[str]]:
	"""Parse SMT-LIB v2 and convert to Circom code. Returns (code, bool_var_names)."""
	circuit_ir: Circuit = parse_smtlib2(smtlib2, solver=solver)

	from src.smt_lib.zk_ir import VariableType
	bool_vars = [f"main.{var.name}" for var in circuit_ir.inputs if var.variable_type == VariableType.BOOLEAN]

	rng = Random(0)
	ir2circom_visitor = IR2CircomVisitorConstrainAssertions(constraint_assignment_probability=1, rng=rng)
	circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)

	emitter = CircomEmitter()
	circom_code = emitter.emit(circom_ir)

	return circom_code, bool_vars


def resolve_hints_for_circom(
	circom_path: Path,
	hint_model: dict,
	opt_flag,
	with_logs: bool,
	compiler: str = "circom",
) -> dict[int, int]:
	"""Map SMT variable names to Circom wire indices using the .sym file."""
	from src.backends.circom.sym_parser import parse_sym_file
	from src.backends.circom.r1cs import _CIRCOMLIB
	import tempfile, subprocess

	circuit_name = circom_path.stem
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_dir_path = Path(temp_dir)
		p = subprocess.run(
			[compiler, str(circom_path), "--sym", opt_flag, "-l", str(_CIRCOMLIB), "-o", str(temp_dir_path)],
			text=True, capture_output=True, check=False,
		)
		if p.returncode != 0:
			log(f"Failed to compile for sym file: {p.stderr}", with_logs)
			return {}

		sym_path = temp_dir_path / f"{circuit_name}.sym"
		if not sym_path.exists():
			return {}

		signal_to_wire = parse_sym_file(sym_path)

	hints = {}
	for var_name, value in hint_model.items():
		signal_name = f"main.{var_name}"
		if signal_name in signal_to_wire:
			int_val = int(value) if isinstance(value, bool) else value
			hints[signal_to_wire[signal_name]] = int_val
	return hints


def build_r1cs_from_circom(
	circom_path: Path,
	*,
	bool_vars: tuple,
	opt_level,
	with_logs: bool,
	compiler: str,
	eliminate_removable: bool = True,
	optimize: bool = True,
):
	"""Compile Circom and return an optimized R1CS with removable wires eliminated."""
	from src.backends.circom.r1cs import get_r1cs_with_sym, parse_r1cs_json

	# Always use get_r1cs_with_sym to detect _removable_ wires in sym file
	bool_signal_names = list(bool_vars) if bool_vars else []
	if bool_signal_names:
		log(f"Boolean signals: {', '.join(bool_signal_names)}", with_logs)
	r1cs_json_str, bool_wire_indices, removable_wire_indices, protected_wire_indices = get_r1cs_with_sym(
		circom_path, opt_flag=opt_level, bool_signal_names=bool_signal_names, compiler=compiler
	)
	if bool_wire_indices:
		log(f"Resolved to wire indices: {bool_wire_indices}", with_logs)

	log("Parsing R1CS JSON...", with_logs)
	r1cs = parse_r1cs_json(r1cs_json_str, bool_wire_indices=bool_wire_indices)

	if eliminate_removable and removable_wire_indices:
		before = r1cs.nConstraints
		r1cs = eliminate_wires(r1cs, removable_wire_indices, protected_wire_indices)
		log(f"Eliminated {before - r1cs.nConstraints} removable constraints ({r1cs.nConstraints} remaining)", with_logs)

	if optimize:
		log("Optimizing R1CS...", with_logs)
		r1cs = optimize_r1cs(r1cs, with_logs=with_logs)
	return r1cs


def solve_circom(circom_path: Path, bool_vars: tuple, with_model: bool, with_logs: bool, solver: str, o0: bool, o1: bool, o2: bool, hint_model: dict | None = None, solving_timeout: int | None = None, hint_probability: float = HINT_PROBABILITY, compiler: str = "circom", dump_r1cs: Path | None = None) -> str:
	"""Compile a Circom circuit, export its R1CS, and solve with an SMT solver. Returns 'sat' or 'unsat'."""
	from src.backends.circom.r1cs import compile_to_r1cs, OptFlag

	if sum([o0, o1, o2]) > 1:
		raise ValueError("Please provide at most one optimization flag among -o0, -o1, -o2.")

	opt_level = OptFlag.O0
	if o1:
		opt_level = OptFlag.O1
	elif o2:
		opt_level = OptFlag.O2

	wire_hints = {}
	if hint_model:
		wire_hints = resolve_hints_for_circom(circom_path, hint_model, opt_level, with_logs, compiler)
		wire_hints = {k: v for k, v in wire_hints.items() if random() < hint_probability}
		log(f"Resolved {len(wire_hints)} hint wire assignments (after probabilistic filtering)", with_logs)

	log(f"Compiling Circom file: {circom_path}...", with_logs)

	if solver == "picus":
		import tempfile
		with tempfile.TemporaryDirectory() as picus_tmp:
			r1cs_path = compile_to_r1cs(circom_path, Path(picus_tmp), opt_flag=opt_level, compiler=compiler)
			log("Solving R1CS using Picus...", with_logs)
			return run_picus(r1cs_path, hints=wire_hints or None, solving_timeout=solving_timeout)

	r1cs = build_r1cs_from_circom(
		circom_path,
		bool_vars=bool_vars,
		opt_level=opt_level,
		with_logs=with_logs,
		compiler=compiler,
		eliminate_removable=True,
		optimize=True,
	)

	if wire_hints:
		r1cs.hints = wire_hints

	if dump_r1cs is not None:
		from src.r1cs.dump import dump_r1cs as _dump_r1cs
		dump_r1cs.write_text(_dump_r1cs(r1cs))

	log("Solving R1CS using a SMT solver...", with_logs)
	solution = solve_r1cs(r1cs, backend=solver, with_logs=with_logs, solving_timeout=solving_timeout)
	return solution_to_str(solution)
