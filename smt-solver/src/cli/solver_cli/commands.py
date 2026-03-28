from pathlib import Path
from uuid import uuid4
import click
from src.smt_lib.simplify import simplify_formula
from src.smt_lib.prune import run_smt_solver
from src.cli.solver_cli.common import (
	ZKDSL, log, dsl_extension, apply_pruning,
)
from src.cli.solver_cli.circom import solve_circom, smtlib2_to_circom
from src.cli.solver_cli.gnark import solve_gnark, smtlib2_to_gnark

@click.command()
@click.argument('smt_lib_path', type=click.Path(exists=True, path_type=Path))
@click.option('--tmp-dir', type=click.Path(path_type=Path), default=Path("/tmp/smt_solver"), help="Temporary directory for intermediate files.")
@click.option("--with-logs", is_flag=True, help="Enable detailed logging.")
@click.option("--zk-dsl", type=click.Choice([ZKDSL.CIRCOM, ZKDSL.GNARK]), default=ZKDSL.CIRCOM, help="Choose the zero-knowledge DSL to use.")
@click.option("--solver", type=click.Choice(["z3", "cvc5", "picus"]), default="z3", help="Choose the SMT solver backend.")
@click.option('--prune', type=int, default=None, help="Prune formula to k variables before solving.")
@click.option('--prune-seed', type=int, default=None, help="Random seed for pruning (for reproducibility).")
@click.option('--with-hints', is_flag=True, help="Solve the SMT query first and inject model values as hints to speed up the oracle.")
@click.option('--no-simplify', is_flag=True, help="Skip Z3 formula simplification before solving.")
def solve(smt_lib_path: Path, tmp_dir: Path, with_logs: bool, zk_dsl: str, solver: str, prune: int, prune_seed: int, with_hints: bool, no_simplify: bool):
	"""
	Solve an SMT-LIB file using a SMT solver.
	SMT_LIB_PATH: Path to the .smt2 file
	"""
	log(f"Using ZK DSL: {zk_dsl}", with_logs=with_logs)
	log(f"Solving SMT-LIB file: {smt_lib_path}...", with_logs=with_logs)
	file_content = smt_lib_path.read_text()

	# Apply pruning if requested
	# Pruning and hints use pysmt in-process — always use z3 to avoid cvc5 Cython conflicts.
	if prune is not None:
		file_content = apply_pruning(
			file_content,
			prune,
			"z3",
			prune_seed,
			smt_lib_path,
			with_logs,
		)

	# Solve SMT query to get model for hints (before any transformation)
	hint_model = None
	if with_hints:
		result, model = run_smt_solver(file_content, solver="z3")
		if result == "sat" and model:
			hint_model = model
			log(f"Hint model obtained: {len(hint_model)} variables", with_logs=with_logs)
		else:
			log(f"No hints available (result: {result})", with_logs=with_logs)

	if not no_simplify:
		file_content = simplify_formula(file_content)
	def _parse_smtlib2(smtlib2: str, dsl: str, solver: str = "z3") -> tuple[str, list[str]]:
		"""Convert SMT-LIB v2 to the target DSL. Returns (code, bool_vars)."""
		if dsl == ZKDSL.CIRCOM:
			return smtlib2_to_circom(smtlib2, solver=solver)
		elif dsl == ZKDSL.GNARK:
			return smtlib2_to_gnark(smtlib2, solver=solver), []
		else:
			raise ValueError(f"Unsupported ZK DSL: {dsl}")

	dsl_code, bool_vars = _parse_smtlib2(file_content, dsl=zk_dsl, solver=solver)

	# save DSL code next to smt_lib_path for debugging purposes when logs are enabled
	if with_logs:
		debug_dsl_path = smt_lib_path.parent / f"{smt_lib_path.stem}_converted.{dsl_extension(zk_dsl)}"
		debug_dsl_path.write_text(dsl_code)
		log(f"Converted {smt_lib_path} to {debug_dsl_path}", with_logs=with_logs)

	# Write code to temporary file
	tmp_dir.mkdir(parents=True, exist_ok=True)

	uuid = uuid4()
	dsl_path = tmp_dir / f"temp-{uuid}.{dsl_extension(zk_dsl)}"
	dsl_path.write_text(dsl_code)

	# Store hint_model in click context for sub-functions to access
	try:
		ctx = click.get_current_context()
		if hint_model:
			ctx.ensure_object(dict)
			ctx.obj["hint_model"] = hint_model
		if zk_dsl == ZKDSL.CIRCOM:
			solve_circom(circom_path=dsl_path, o0=False, o1=False, o2=True, with_logs=with_logs, with_model=False, solver=solver, bool_vars=tuple(bool_vars))
		elif zk_dsl == ZKDSL.GNARK:
			solve_gnark(gnark_path=dsl_path, with_logs=with_logs, with_model=False, solver=solver, tmp_dir=tmp_dir)
		else:
			raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")
	finally:
		# Remove temporary DSL file, even if compilation/solving fails.
		if dsl_path.exists():
			dsl_path.unlink()
