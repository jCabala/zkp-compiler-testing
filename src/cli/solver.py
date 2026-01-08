from pathlib import Path
import click
from src.r1cs import get_r1cs_json

# --------------------------- Solve Circom Command ----------------------------------
@click.command()
@click.argument('circom_path', type=click.Path(exists=True, path_type=Path))
def solve_circom_command(circom_path: Path):
	"""
	Compile a Circom circuit, export its R1CS representation, and use SMT solver to find a solution.
	CIRCOM_PATH: Path to the .circom file
	"""
	from src.r1cs.ir import parse_r1cs_json
	from src.r1cs.solve import solve_r1cs

	click.echo(f"Compiling {circom_path}...")
	r1cs_json_str = get_r1cs_json(circom_path)

	click.echo("Parsing R1CS JSON...")
	r1cs = parse_r1cs_json(r1cs_json_str)

	click.echo("Solving R1CS using Z3...")
	solution = solve_r1cs(r1cs)

	if solution.satisfiable:
		click.echo("✓ Solution found:")
		for var, val in solution.model.items():
			click.echo(f"  {var} = {val}")
	else:
		click.echo("✗ No solution exists.")
