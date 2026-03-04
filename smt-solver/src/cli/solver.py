import os
import subprocess
from pathlib import Path
from random import Random
from uuid import uuid4
import click

_GO_CACHE_CLEAN_INTERVAL = 1000
_GO_CACHE_COUNTER_FILE = ".go_run_count"

def _maybe_clean_go_cache() -> None:
    """Periodically run `go clean -cache` to prevent unbounded GOCACHE growth.

    Each `go run` on a unique circuit adds a cache entry that is never reused.
    Because cli.py is a short-lived subprocess per circuit, state is persisted
    in a counter file inside GOCACHE so it survives across invocations.
    """
    gocache = os.environ.get("GOCACHE")
    if not gocache:
        return
    counter_path = Path(gocache) / _GO_CACHE_COUNTER_FILE
    try:
        count = int(counter_path.read_text()) if counter_path.exists() else 0
        count += 1
        counter_path.write_text(str(count))
        if count % _GO_CACHE_CLEAN_INTERVAL == 0:
            subprocess.run(["go", "clean", "-cache"], capture_output=True)
            counter_path.write_text("0")
    except OSError:
        pass  # non-fatal: cache grows a bit more until next successful clean
from src.smt_lib.simplify import simplify_formula
from src.smt_lib.smt_lib_parser import parse_smtlib2_core
from src.smt_lib.zk_ir import Circuit
from src.smt_lib.prune import prune_formula
from src.r1cs.solve import solve_r1cs
from src.r1cs.optimize import optimize_r1cs
from src.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from src.backends.circom.emitter import EmitVisitor as CircomEmitter
from src.backends.gnark.emitter import EmitVisitor as GnarkEmitter
from src.backends.gnark.ir2gnark import IR2GnarkVisitor

# --------------------------- Commands ----------------------------------
@click.command()
@click.argument('circom_path', type=click.Path(exists=True, path_type=Path))
@click.option('--bool-vars', multiple=True, help="Signal names to treat as boolean (e.g., main.flag, main.arr[0]). Can be specified multiple times.")
@click.option('--with-model', is_flag=True, help="Output the model if satisfiable.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option('-o0', is_flag=True, help="Use optimization flag o0 for Circom compilation.")
@click.option('-o1', is_flag=True, help="Use optimization flag o1 for Circom compilation.")
@click.option('-o2', is_flag=True, help="Use optimization flag o2 for Circom compilation.")
@click.option('--solver', type=click.Choice(["z3", "cvc5"]), default="z3", help="Choose the SMT solver backend.")
def solve_circom_command(circom_path: Path, bool_vars: tuple, with_model: bool, with_logs: bool, solver: str, o0: bool, o1: bool, o2: bool):
	"""
	Compile a Circom circuit, export its R1CS representation, and use SMT solver to find a solution.
	CIRCOM_PATH: Path to the .circom file`
	"""
	from src.backends.circom.r1cs import get_r1cs_json, get_r1cs_with_sym, parse_r1cs_json, OptFlag

	if sum([o0, o1, o2]) > 1:
		raise click.UsageError("Please provide at most one optimization flag among -o0, -o1, -o2.")
	
	opt_level = OptFlag.O0
	if o1:
		opt_level = OptFlag.O1
	elif o2:
		opt_level = OptFlag.O2
	
	if solver == "picus":
		from src.picus.solve_picus import solve_picus
		_log("Solving R1CS using Picus...", with_logs)
		_run_picus(circom_path)
		return

	_log(f"Compiling Circom file: {circom_path}...", with_logs)
	
	# If bool_vars specified, use get_r1cs_with_sym to resolve signal names
	if bool_vars:
		bool_signal_names = list(bool_vars)
		_log(f"Boolean signals: {', '.join(bool_signal_names)}", with_logs)
		r1cs_json_str, bool_wire_indices = get_r1cs_with_sym(circom_path, opt_flag=opt_level, bool_signal_names=bool_signal_names)
		_log(f"Resolved to wire indices: {bool_wire_indices}", with_logs)
	else:
		r1cs_json_str = get_r1cs_json(circom_path, opt_flag=opt_level)
		bool_wire_indices = set()

	_log("Parsing R1CS JSON...", with_logs)
	r1cs = parse_r1cs_json(r1cs_json_str, bool_wire_indices=bool_wire_indices)

	_log("Optimizing R1CS...", with_logs)
	r1cs = optimize_r1cs(r1cs, with_logs=with_logs)

	_log("Solving R1CS using a SMT solver...", with_logs)
	solution = solve_r1cs(r1cs, backend=solver, with_logs=with_logs)
	_log_smt_results(solution, with_model)

@click.command()
@click.argument('gnark_path', type=click.Path(exists=True, path_type=Path))
@click.option('--with-model', is_flag=True, help="Output the model if satisfiable.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option("--solver", type=click.Choice(["z3", "cvc5", "picus"]), default="z3", help="Choose the SMT solver backend.")
@click.option("--tmp-dir", type=click.Path(path_type=Path), default=Path("/tmp/smt_solver"), help="Temporary directory for intermediate files.")
def solve_gnark_command(gnark_path: Path, with_model: bool, with_logs: bool, solver: str, tmp_dir: Path):
	"""
	Compile a GNARK (Go) circuit, export its R1CS representation, and use SMT solver to find a solution.
	GNARK_PATH: Path to the .go file
	"""
	from src.backends.gnark.r1cs import get_r1cs_sr1cs, parse_sr1cs

	_log(f"Compiling GNARK file: {gnark_path}...", with_logs=with_logs)
	r1cs_sr1cs_str = get_r1cs_sr1cs(gnark_path)
	_maybe_clean_go_cache()
	
	if solver == "picus":
		from src.picus.solve_picus import solve_picus
		_log("Solving R1CS using Picus...", with_logs)
		tmp_dir.mkdir(parents=True, exist_ok=True)
		tmp_sr1cs_path = tmp_dir / f"temp-{uuid4()}.sr1cs"
		try:
			tmp_sr1cs_path.write_text(r1cs_sr1cs_str)
			_run_picus(tmp_sr1cs_path)
		finally:
			if tmp_sr1cs_path.exists():
				tmp_sr1cs_path.unlink()
		return

	_log("Parsing R1CS SR1CS...", with_logs)
	r1cs = parse_sr1cs(r1cs_sr1cs_str)
	
	_log("Optimizing R1CS...", with_logs)
	r1cs = optimize_r1cs(r1cs, with_logs=with_logs)
	
	_log("Solving R1CS using a SMT solver...", with_logs)
	solution = solve_r1cs(r1cs, backend=solver, with_logs=with_logs)
	_log_smt_results(solution, with_model)

class ZKDSL:
	CIRCOM = "circom"
	GNARK="gnark"

@click.command()
@click.argument('smt_lib_path', type=click.Path(exists=True, path_type=Path))
@click.option('--tmp-dir', type=click.Path(path_type=Path), default=Path("/tmp/smt_solver"), help="Temporary directory for intermediate files.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option("--zk-dsl", type=click.Choice([ZKDSL.CIRCOM, ZKDSL.GNARK]), default=ZKDSL.CIRCOM, help="Choose the zero-knowledge DSL to use.")
@click.option("--solver", type=click.Choice(["z3", "cvc5", "picus"]), default="z3", help="Choose the SMT solver backend.")
@click.option('--prune', type=int, default=None, help="Prune formula to k variables before solving.")
@click.option('--prune-seed', type=int, default=None, help="Random seed for pruning (for reproducibility).")

def solve(smt_lib_path: Path, tmp_dir: Path, with_logs: bool, zk_dsl: str, solver: str, prune: int, prune_seed: int):
	"""
	Solve an SMT-LIB file using a SMT solver.
	SMT_LIB_PATH: Path to the .smt2 file
	"""
	_log(f"Using ZK DSL: {zk_dsl}", with_logs=with_logs)
	_log(f"Solving SMT-LIB file: {smt_lib_path}...", with_logs=with_logs)
	file_content = smt_lib_path.read_text()
	
	# Apply pruning if requested
	# Pruning needs an actual SMT solver (z3/cvc5) to determine SAT/UNSAT and extract models.
	# Picus is an external tool, not a pySMT backend, so fall back to z3 for pruning.
	if prune is not None:
		prune_solver = "z3" if solver == "picus" else solver
		file_content = _apply_pruning(
			file_content,
			prune,
			prune_solver,
			prune_seed,
			smt_lib_path,
			with_logs,
		)
	
	file_content = simplify_formula(file_content)
	dsl_code, bool_vars = _parse_smtlib2(file_content, dsl=zk_dsl, solver=solver)

	# save DSL code next to smt_lib_path for debugging purposes when logs are enabled
	if with_logs:
		debug_dsl_path = smt_lib_path.parent / f"{smt_lib_path.stem}_converted.{_dsl_extension(zk_dsl)}"
		debug_dsl_path.write_text(dsl_code)
		_log(f"Converted {smt_lib_path} to {debug_dsl_path}", with_logs=with_logs)

	# Write code to temporary file
	tmp_dir.mkdir(parents=True, exist_ok=True)

	uuid = uuid4()
	dsl_path = tmp_dir / f"temp-{uuid}.{_dsl_extension(zk_dsl)}"
	dsl_path.write_text(dsl_code)

	# Now use the previously defined command to solve the Circom file
	try:
		ctx = click.get_current_context()
		if zk_dsl == ZKDSL.CIRCOM:
			ctx.invoke(solve_circom_command, circom_path=dsl_path, o0=False, o1=False, o2=True, with_logs=with_logs, with_model=False, solver=solver, bool_vars=tuple(bool_vars))
		elif zk_dsl == ZKDSL.GNARK:
			ctx.invoke(solve_gnark_command, gnark_path=dsl_path, with_logs=with_logs, with_model=False, solver=solver, tmp_dir=tmp_dir)
		else:
			raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")
	finally:
		# Remove temporary DSL file, even if compilation/solving fails.
		if dsl_path.exists():
			dsl_path.unlink()

# --------------------------- Helper Functions ----------------------------------

def _apply_pruning(
	file_content: str,
	k: int,
	solver: str,
	seed: int,
	smt_lib_path: Path,
	with_logs: bool,
) -> str:
	"""Apply pruning to SMT-LIB formula and log results."""
	_log(f"Pruning formula to {k} variables...", with_logs=with_logs)
	_log("Pruning mode: keep complete fused pairs", with_logs=with_logs)
	pruned_content, metadata = prune_formula(
		file_content, 
		k=k, 
		solver=solver,
		seed=seed,
	)
	
	if metadata.get("pruned", False):
		_log(f"Pruned: {metadata['replaced_vars']} vars replaced, {metadata['kept_vars']} kept (original result: {metadata['original_result']})", with_logs=with_logs)
		# Save pruned formula for debugging
		if with_logs:
			pruned_path = smt_lib_path.parent / f"{smt_lib_path.stem}_pruned.smt2"
			pruned_path.write_text(pruned_content)
			_log(f"Pruned formula saved to {pruned_path}", with_logs=with_logs)
	else:
		_log(f"Pruning skipped: {metadata.get('reason', 'unknown reason')}", with_logs=with_logs)
	
	return pruned_content

def _log(message: str, with_logs: bool):
	if with_logs:
		click.echo(message)

def _log_smt_results(solution, with_model: bool ):
	if solution.satisfiable:
		click.echo("sat")
	else:
		click.echo("unsat")

	if solution.satisfiable and with_model:
		click.echo("Model:")
		for var, value in solution.model.items():
			click.echo(f"  {var} = {value}")

def _parse_smtlib2(smtlib2: str, dsl: ZKDSL, solver: str = "z3") -> tuple[str, list[str]]:
	def _smtlib2_to_circom(smtlib2: str) -> tuple[str, list[str]]:
		# Parse SMT-LIB v2 to Circuit IR
		circuit_ir: Circuit = parse_smtlib2_core(smtlib2, solver=solver)
		
		# Extract boolean variables for --bool-vars
		from src.smt_lib.zk_ir import VariableType
		bool_vars = [f"main.{var.name}" for var in circuit_ir.inputs if var.variable_type == VariableType.BOOLEAN]

		# Convert Circuit IR to Circom IR
		rng = Random(0)
		ir2circom_visitor = IR2CircomVisitorConstrainAssertions(constraint_assignment_probability=1, rng=rng)
		circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)

		# Emit Circom code from Circom IR
		emitter = CircomEmitter()
		circom_code = emitter.emit(circom_ir)

		return circom_code, bool_vars


	def _smtlib2_to_gnark(smtlib2: str) -> str:
		circuit_ir: Circuit = parse_smtlib2_core(smtlib2, solver=solver)
		ir2gnark_visitor = IR2GnarkVisitor()
		gnark_ir = ir2gnark_visitor.visit_circuit(circuit_ir)
		emitter = GnarkEmitter()
		gnark_code = emitter.emit(gnark_ir)

		return gnark_code
	
	if dsl == ZKDSL.CIRCOM:
		return _smtlib2_to_circom(smtlib2)
	elif dsl == ZKDSL.GNARK:
		# Gnark doesn't support bool vars extraction yet
		return _smtlib2_to_gnark(smtlib2), []
	else:
		raise ValueError(f"Unsupported ZK DSL: {dsl}")

def _dsl_extension(zk_dsl: ZKDSL) -> str:
	if zk_dsl == ZKDSL.CIRCOM:
		return "circom"
	elif zk_dsl == ZKDSL.GNARK:
		return "go"
	else:
		raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")
	
def _run_picus(input_path: Path) -> None:
	from src.picus.solve_picus import solve_picus

	result = solve_picus(input_path)

	if result.result == "properly_constrained":
		click.echo("sat")
	elif result.result == "underconstrained":
		click.echo("unsat")
	elif result.result == "unknown":
		raise click.ClickException("Picus returned unknown result")
	else:
		output_preview = (result.output or "").strip().splitlines()
		if output_preview:
			output_preview = output_preview[-1]
		else:
			output_preview = "<no output>"
		raise click.ClickException(
			f"Picus failed (exit={result.exit_code}): {output_preview}"
		)
