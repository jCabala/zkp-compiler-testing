from pathlib import Path
from random import Random
from uuid import uuid4
import click
from src.smt_lib.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from src.smt_lib.backends.circom.emitter import EmitVisitor as CircomEmitter
from src.smt_lib.smt_lib_parser import parse_smtlib2_core
from src.smt_lib.zk_ir import Circuit
from src.r1cs import get_r1cs_json, OptFlag

def log(message: str, with_logs: bool):
	if with_logs:
		click.echo(message)

# --------------------------- Solve Circom Command ----------------------------------
@click.command()
@click.argument('circom_path', type=click.Path(exists=True, path_type=Path))
@click.option('--bool-vars', is_flag=True, help="Treat all variables as booleans.")
@click.option('--with-model', is_flag=True, help="Output the model if satisfiable.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option('-o0', is_flag=True, help="Use optimization flag o0 for Circom compilation.")
@click.option('-o1', is_flag=True, help="Use optimization flag o1 for Circom compilation.")
@click.option('-o2', is_flag=True, help="Use optimization flag o2 for Circom compilation.")
def solve_circom_command(circom_path: Path, bool_vars: bool, with_model: bool, with_logs: bool, o0: bool, o1: bool, o2: bool):
	"""
	Compile a Circom circuit, export its R1CS representation, and use SMT solver to find a solution.
	CIRCOM_PATH: Path to the .circom file
	bool-vars: Treat all variables as booleans. Speeds up the SMT a lot.
	"""
	from src.r1cs.ir import parse_r1cs_json
	from src.r1cs.solve import solve_r1cs

	if sum([o0, o1, o2]) > 1:
		raise click.UsageError("Please provide at most one optimization flag among -o0, -o1, -o2.")
	
	opt_level = OptFlag.O0
	if o1:
		opt_level = OptFlag.O1
	elif o2:
		opt_level = OptFlag.O2
		
	log(f"Compiling Circom file: {circom_path}...", with_logs)
	r1cs_json_str = get_r1cs_json(circom_path, opt_flag=opt_level)

	log("Parsing R1CS JSON...", with_logs)
	r1cs = parse_r1cs_json(r1cs_json_str)

	log("Solving R1CS using Z3...", with_logs)
	solution = solve_r1cs(r1cs, bool_vars=bool_vars)

	if solution.satisfiable:
		click.echo("sat")
		if with_model:
			click.echo(solution.model)
	else:
		click.echo("unsat")

@click.command()
@click.argument('smt_lib_path', type=click.Path(exists=True, path_type=Path))
@click.option('--tmp-dir', type=click.Path(path_type=Path), default=Path("/tmp/smt_solver"), help="Temporary directory for intermediate files.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")

def solve(smt_lib_path: Path, tmp_dir: Path = Path("/tmp/smt_solver"), with_logs: bool = False):
	"""
	Solve an SMT-LIB file using Z3 solver.
	SMT_LIB_PATH: Path to the .smt2 file
	"""

	def smtlib2_to_circom(smtlib2: str) -> str:
		# Parse SMT-LIB v2 to Circuit IR
		circuit_ir: Circuit = parse_smtlib2_core(smtlib2)

		# Convert Circuit IR to Circom IR
		rng = Random(0)
		ir2circom_visitor = IR2CircomVisitorConstrainAssertions(constraint_assignment_probability=1, rng=rng)
		circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)

		# Emit Circom code from Circom IR
		emitter = CircomEmitter()
		circom_code = emitter.emit(circom_ir)

		return circom_code

	log(f"Solving SMT-LIB file: {smt_lib_path}...", with_logs=with_logs)
	file_content = smt_lib_path.read_text()
	circom_code = smtlib2_to_circom(file_content)

	# Write Circom code to temporary file
	tmp_dir.mkdir(parents=True, exist_ok=True)

	uuid = uuid4()
	circom_path = tmp_dir / f"temp-{uuid}.circom"
	circom_path.write_text(circom_code)

	# Now use the previously defined command to solve the Circom file
	ctx = click.get_current_context()
	ctx.invoke(solve_circom_command, circom_path=circom_path, bool_vars=True, o0=False, o1=False, o2=True, with_logs=with_logs)

	# Remove temporary Circom file
	circom_path.unlink()
