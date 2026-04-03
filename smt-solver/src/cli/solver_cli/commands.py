from pathlib import Path
from uuid import uuid4
from time import monotonic
import json
import click

from src.smt_lib.simplify import simplify_formula
from src.smt_lib.prune import run_smt_solver_models
from src.cli.solver_cli.common import (
	ZKDSL, log, dsl_extension, apply_pruning,
)
from src.cli.solver_cli.circom import solve_circom, smtlib2_to_circom
from src.cli.solver_cli.gnark import solve_gnark, smtlib2_to_gnark
from src.cli.solver_cli.adaptive_hints import load_state, save_state, record_run, HINT_MODELS

@click.command()
@click.argument('smt_lib_path', type=click.Path(exists=True, path_type=Path))
@click.option('--config', type=click.Path(exists=True, path_type=Path), default=None, help="JSON file with default option values (CLI flags override).")
@click.option('--tmp-dir', type=click.Path(path_type=Path), default=None, help="Temporary directory for intermediate files.")
@click.option("--with-logs", is_flag=True, default=None, help="Enable detailed logging.")
@click.option("--zk-dsl", type=click.Choice([ZKDSL.CIRCOM, ZKDSL.GNARK]), default=None, help="Choose the zero-knowledge DSL to use.")
@click.option("--solver", type=click.Choice(["z3", "cvc5", "picus"]), default=None, help="Choose the SMT solver backend.")
@click.option('--prune', type=int, default=None, help="Prune formula to k variables before solving.")
@click.option('--prune-seed', type=int, default=None, help="Random seed for pruning (for reproducibility).")
@click.option('--without-hints', is_flag=True, default=None, help="Disable injection of hint model values (hints are enabled by default).")
@click.option('--no-simplify', is_flag=True, default=None, help="Skip Z3 formula simplification before solving.")
@click.option('--solving-timeout', type=int, default=None, help="Timeout in seconds for the SMT solving step. Returns 'unknown' if exceeded.")
def solve(smt_lib_path: Path, config: Path, tmp_dir: Path, with_logs: bool, zk_dsl: str, solver: str, prune: int, prune_seed: int, without_hints: bool, no_simplify: bool, solving_timeout: int):
	"""
	Solve an SMT-LIB file using a SMT solver.
	SMT_LIB_PATH: Path to the .smt2 file
	"""
	# Load JSON config; CLI flags (non-None) take precedence over config values
	cfg = json.loads(config.read_text()) if config is not None else {}

	def _opt(val, key, default):
		"""Return CLI val if set, else config value, else hardcoded default."""
		if val is not None:
			return val
		return cfg.get(key, default)

	tmp_dir    = _opt(tmp_dir,    "tmp_dir",     Path("/tmp/smt_solver"))
	with_logs  = _opt(with_logs,  "with_logs",   False)
	zk_dsl     = _opt(zk_dsl,     "zk_dsl",      ZKDSL.CIRCOM)
	solver     = _opt(solver,     "solver",      "z3")
	prune      = _opt(prune,      "prune",       None)
	prune_seed    = _opt(prune_seed,    "prune_seed",    None)
	without_hints = _opt(without_hints, "without_hints", False)
	no_simplify      = _opt(no_simplify,      "no_simplify",      False)
	solving_timeout  = _opt(solving_timeout,  "solving_timeout",  None)
	with_hints = not without_hints

	if isinstance(tmp_dir, str):
		tmp_dir = Path(tmp_dir)

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

	# Load adaptive hints state and use current parameters
	adaptive_state = load_state(tmp_dir)
	log(f"Adaptive hints: models={adaptive_state.hint_models}, probability={adaptive_state.hint_probability}", with_logs=with_logs)

	# Collect hint models (before any transformation)
	hint_model_list: list[dict] = []
	if with_hints:
		_, models = run_smt_solver_models(file_content, solver="z3", max_models=adaptive_state.hint_models)
		hint_model_list = models
		log(f"Obtained {len(hint_model_list)} hint model(s)", with_logs=with_logs)
		if not hint_model_list:
			log("No hints available (formula unsat or no model returned)", with_logs=with_logs)

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

	def _run_oracle(hint_model: dict | None) -> str:
		if zk_dsl == ZKDSL.CIRCOM:
			return solve_circom(circom_path=dsl_path, o0=False, o1=False, o2=True, with_logs=with_logs, with_model=False, solver=solver, bool_vars=tuple(bool_vars), hint_model=hint_model, solving_timeout=solving_timeout, hint_probability=adaptive_state.hint_probability)
		elif zk_dsl == ZKDSL.GNARK:
			return solve_gnark(gnark_path=dsl_path, with_logs=with_logs, with_model=False, solver=solver, tmp_dir=tmp_dir, hint_model=hint_model, solving_timeout=solving_timeout, hint_probability=adaptive_state.hint_probability)
		else:
			raise ValueError(f"Unsupported ZK DSL: {zk_dsl}")

	try:
		# Run oracle once per hint model; if no hints, run once with no hints
		runs = hint_model_list if hint_model_list else [None]
		results = []
		for i, hint_model in enumerate(runs):
			log(f"Oracle run {i + 1}/{len(runs)}", with_logs=with_logs)
			t0 = monotonic()
			results.append(_run_oracle(hint_model))
			elapsed = monotonic() - t0
			adaptive_state = record_run(adaptive_state, elapsed, solving_timeout)

		save_state(tmp_dir, adaptive_state)

		# sat only if every run returned sat; unknown if any timed out
		if any(r == "unknown" for r in results):
			final = "unknown"
		elif all(r == "sat" for r in results):
			final = "sat"
		else:
			final = "unsat"
		click.echo(final)
	finally:
		if dsl_path.exists():
			dsl_path.unlink()
