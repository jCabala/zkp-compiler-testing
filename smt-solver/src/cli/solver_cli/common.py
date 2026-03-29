from pathlib import Path
import click
from src.smt_lib.prune import prune_formula


class ZKDSL:
	CIRCOM = "circom"
	GNARK = "gnark"


def log(message: str, with_logs: bool):
	if with_logs:
		click.echo(message)


def log_smt_results(solution, with_model: bool):
	if solution.satisfiable:
		click.echo("sat")
	else:
		click.echo("unsat")

	if solution.satisfiable and with_model:
		click.echo("Model:")
		for var, value in solution.model.items():
			click.echo(f"  {var} = {value}")


def dsl_extension(zk_dsl: str) -> str:
	if zk_dsl == ZKDSL.CIRCOM:
		return "circom"
	elif zk_dsl == ZKDSL.GNARK:
		return "go"
	else:
		raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")


def get_hint_model_from_ctx() -> dict | None:
	"""Retrieve hint_model stored in click context by the solve command."""
	ctx = click.get_current_context(silent=True)
	if ctx and ctx.obj and isinstance(ctx.obj, dict):
		return ctx.obj.get("hint_model")
	return None


def apply_pruning(
	file_content: str,
	k: int,
	solver: str,
	seed: int,
	smt_lib_path: Path,
	with_logs: bool,
) -> str:
	"""Apply pruning to SMT-LIB formula and log results."""
	log(f"Pruning formula to {k} variables...", with_logs=with_logs)
	log("Pruning mode: keep complete fused pairs", with_logs=with_logs)
	pruned_content, metadata = prune_formula(
		file_content,
		k=k,
		solver=solver,
		seed=seed,
	)

	if metadata.get("pruned", False):
		log(f"Pruned: {metadata['replaced_vars']} vars replaced, {metadata['kept_vars']} kept (original result: {metadata['original_result']})", with_logs=with_logs)
		if with_logs:
			pruned_path = smt_lib_path.parent / f"{smt_lib_path.stem}_pruned.smt2"
			pruned_path.write_text(pruned_content)
			log(f"Pruned formula saved to {pruned_path}", with_logs=with_logs)
	else:
		log(f"Pruning skipped: {metadata.get('reason', 'unknown reason')}", with_logs=with_logs)

	return pruned_content



def run_picus(input_path: Path, hints: dict[int, int] | None = None) -> None:
	from src.picus.solve_picus import solve_picus

	result = solve_picus(input_path, hints=hints or None)

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
