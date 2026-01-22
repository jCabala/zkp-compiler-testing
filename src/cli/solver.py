from pathlib import Path
from random import Random
from uuid import uuid4
import click
from src.smt_lib.smt_lib_parser import parse_smtlib2_core
from src.smt_lib.zk_ir import Circuit
from src.r1cs.solve import solve_r1cs
from src.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from src.backends.circom.emitter import EmitVisitor as CircomEmitter
from src.backends.gnark.emitter import EmitVisitor as GnarkEmitter
from src.backends.gnark.ir2gnark import IR2GnarkVisitor

# --------------------------- Commands ----------------------------------
@click.command()
@click.argument('circom_path', type=click.Path(exists=True, path_type=Path))
@click.option('--bool-vars', is_flag=True, help="Treat all variables as booleans.")
@click.option('--with-model', is_flag=True, help="Output the model if satisfiable.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option('-o0', is_flag=True, help="Use optimization flag o0 for Circom compilation.")
@click.option('-o1', is_flag=True, help="Use optimization flag o1 for Circom compilation.")
@click.option('-o2', is_flag=True, help="Use optimization flag o2 for Circom compilation.")
@click.option('--solver', type=click.Choice(["z3", "cvc5"]), default="z3", help="Choose the SMT solver backend.")
def solve_circom_command(circom_path: Path, bool_vars: bool, with_model: bool, with_logs: bool, solver: str, o0: bool, o1: bool, o2: bool):
	"""
	Compile a Circom circuit, export its R1CS representation, and use SMT solver to find a solution.
	CIRCOM_PATH: Path to the .circom file
	bool-vars: Treat all variables as booleans. Speeds up the SMT a lot.
	"""
	from src.backends.circom.r1cs import get_r1cs_json, parse_r1cs_json, OptFlag

	if sum([o0, o1, o2]) > 1:
		raise click.UsageError("Please provide at most one optimization flag among -o0, -o1, -o2.")
	
	opt_level = OptFlag.O0
	if o1:
		opt_level = OptFlag.O1
	elif o2:
		opt_level = OptFlag.O2
		
	_log(f"Compiling Circom file: {circom_path}...", with_logs)
	r1cs_json_str = get_r1cs_json(circom_path, opt_flag=opt_level)

	_log("Parsing R1CS JSON...", with_logs)
	r1cs = parse_r1cs_json(r1cs_json_str)

	_log("Solving R1CS using a SMT solver...", with_logs)
	solution = solve_r1cs(r1cs, bool_vars=bool_vars, backend=solver, with_logs=with_logs)
	_log_smt_results(solution, with_model)

@click.command()
@click.argument('gnark_path', type=click.Path(exists=True, path_type=Path))
@click.option('--bool-vars', is_flag=True, help="Treat all variables as booleans.")
@click.option('--with-model', is_flag=True, help="Output the model if satisfiable.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option("--solver", type=click.Choice(["z3", "cvc5"]), default="z3", help="Choose the SMT solver backend.")
def solve_gnark_command(gnark_path: Path, bool_vars: bool, with_model: bool, with_logs: bool, solver: str):
	"""
	Compile a GNARK (Go) circuit, export its R1CS representation, and use SMT solver to find a solution.
	GNARK_PATH: Path to the .go file
	bool-vars: Treat all variables as booleans. Speeds up the SMT a lot.
	"""
	from src.backends.gnark.r1cs import get_r1cs_json, parse_r1cs_json

	_log(f"Compiling GNARK file: {gnark_path}...", with_logs=with_logs)
	r1cs_json_str = get_r1cs_json(gnark_path)
	# print(r1cs_json_str)

	_log("Parsing R1CS JSON...", with_logs)
	r1cs = parse_r1cs_json(r1cs_json_str)

	_log("Solving R1CS using a SMT solver...", with_logs)
	solution = solve_r1cs(r1cs, bool_vars=bool_vars, backend=solver, with_logs=with_logs)
	_log_smt_results(solution, with_model)

class ZKDSL:
	CIRCOM = "circom"
	GNARK="gnark"

@click.command()
@click.argument('smt_lib_path', type=click.Path(exists=True, path_type=Path))
@click.option('--tmp-dir', type=click.Path(path_type=Path), default=Path("/tmp/smt_solver"), help="Temporary directory for intermediate files.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option("--zk-dsl", type=click.Choice([ZKDSL.CIRCOM, ZKDSL.GNARK]), default=ZKDSL.CIRCOM, help="Choose the zero-knowledge DSL to use.")
@click.option("--bool-vars", is_flag=True, help="Treat all variables as booleans.")
@click.option("--solver", type=click.Choice(["z3", "cvc5"]), default="z3", help="Choose the SMT solver backend.")

def solve(smt_lib_path: Path, tmp_dir: Path, with_logs: bool, zk_dsl: str, bool_vars: bool, solver: str):
	"""
	Solve an SMT-LIB file using a SMT solver.
	SMT_LIB_PATH: Path to the .smt2 file
	"""
	_log(f"Using ZK DSL: {zk_dsl}", with_logs=with_logs)
	_log(f"Solving SMT-LIB file: {smt_lib_path}...", with_logs=with_logs)
	file_content = smt_lib_path.read_text()
	dsl_code = _parse_smtlib2(file_content, dsl=zk_dsl, solver=solver)

	# Write code to temporary file
	tmp_dir.mkdir(parents=True, exist_ok=True)

	uuid = uuid4()
	dsl_path = tmp_dir / f"temp-{uuid}.{_dsl_extension(zk_dsl)}"
	dsl_path.write_text(dsl_code)

	# Now use the previously defined command to solve the Circom file
	ctx = click.get_current_context()
	if zk_dsl == ZKDSL.CIRCOM:
		ctx.invoke(solve_circom_command, circom_path=dsl_path, bool_vars=bool_vars, o0=False, o1=False, o2=True, with_logs=with_logs, with_model=False, solver=solver)
	elif zk_dsl == ZKDSL.GNARK:
		ctx.invoke(solve_gnark_command, gnark_path=dsl_path, bool_vars=bool_vars, with_logs=with_logs, with_model=False, solver=solver)
	else:
		raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")

	# Remove temporary Circom file
	dsl_path.unlink()

# --------------------------- Helper Functions ----------------------------------

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

def _parse_smtlib2(smtlib2: str, dsl: ZKDSL, solver: str = "z3") -> str:
	def _smtlib2_to_circom(smtlib2: str) -> str:
		# Parse SMT-LIB v2 to Circuit IR
		circuit_ir: Circuit = parse_smtlib2_core(smtlib2, solver=solver)

		# Convert Circuit IR to Circom IR
		rng = Random(0)
		ir2circom_visitor = IR2CircomVisitorConstrainAssertions(constraint_assignment_probability=1, rng=rng)
		circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)

		# Emit Circom code from Circom IR
		emitter = CircomEmitter()
		circom_code = emitter.emit(circom_ir)

		return circom_code


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
		return _smtlib2_to_gnark(smtlib2)
	else:
		raise ValueError(f"Unsupported ZK DSL: {dsl}")

def _dsl_extension(zk_dsl: ZKDSL) -> str:
	if zk_dsl == ZKDSL.CIRCOM:
		return "circom"
	elif zk_dsl == ZKDSL.GNARK:
		return "go"
	else:
		raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")