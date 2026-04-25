from pathlib import Path
import click

from src.cli.benchmark_gen_cli.bool_to_ff import generate_ff_benchmarks, generate_ff_benchmark_suite
from src.cli.benchmark_gen_cli.sudoku import sudoku17_to_smtlib2
from src.cli.benchmark_gen_cli.filter_ff_benchmarks import filter_ff_benchmarks


@click.command(name="bool-smt-to-ff")
@click.argument("in_folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--dsl", type=click.Choice(["circom", "gnark", "zokrates"]), required=True, help="Compiler backend to use.")
@click.option("--compiler", default=None, help="Compiler binary (circom for circom, go for gnark).")
@click.option("--max-out", type=int, default=None, help="Maximum number of files to convert.")
@click.option(
	"--opt-level",
	type=click.Choice(["O0", "O1", "O2"]),
	default="O2",
	show_default=True,
	help="Circom optimization level. Ignored for gnark.",
)
@click.option("--suffix", default=None, help="Optional suffix appended to output filenames.")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip outputs that already exist.")
@click.option("--continue-on-error", is_flag=True, default=False, help="Keep going if a file fails.")
@click.option("--with-logs", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--keep-intermediate", type=click.Path(path_type=Path), default=None, help="Save intermediate DSL files to this folder.")
@click.option("--max-vars", type=int, default=None, help="Only emit outputs whose compiled R1CS has nVars <= this threshold.")
def bool_smt_to_ff_command(
	in_folder: Path,
	out_folder: Path,
	dsl: str,
	compiler: str | None,
	max_out: int | None,
	opt_level: str,
	suffix: str | None,
	skip_existing: bool,
	continue_on_error: bool,
	with_logs: bool,
	keep_intermediate: Path | None,
	max_vars: int | None,
):
	"""
	Batch-convert boolean SMT-LIB v2 files into finite-field SMT-LIB (QF_FF).

	IN_FOLDER: folder with .smt2 files (boolean-only core)
	OUT_FOLDER: output folder for QF_FF .smt2 files
	"""
	try:
		generate_ff_benchmarks(
			in_folder=in_folder,
			out_folder=out_folder,
			dsl=dsl,
			compiler=compiler,
			max_out=max_out,
			opt_level=opt_level,
			suffix=suffix,
			max_vars=max_vars,
			skip_existing=skip_existing,
			continue_on_error=continue_on_error,
			with_logs=with_logs,
			keep_intermediate=keep_intermediate,
			log=click.echo,
		)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


@click.command(name="generate-ff-benchmark-suite")
@click.argument("in_folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("out_base", type=click.Path(path_type=Path))
@click.option("--max-vars", type=int, required=True, help="Accept a generated FF benchmark only if its compiled R1CS has nVars <= this threshold.")
@click.option("--circom-compiler", default=None, help="Circom compiler binary.")
@click.option("--gnark-compiler", default=None, help="Gnark compiler binary.")
@click.option("--zokrates-compiler", default=None, help="ZoKrates compiler binary.")
@click.option(
	"--circom-opt-level",
	"circom_opt_levels",
	type=click.Choice(["O0", "O1", "O2"]),
	multiple=True,
	default=("O0", "O1", "O2"),
	show_default=True,
	help="Circom optimization levels to generate.",
)
@click.option("--max-out", type=int, default=None, help="Maximum number of input files to process.")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip outputs that already exist.")
@click.option("--continue-on-error", is_flag=True, default=False, help="Keep going if a file/backend fails.")
@click.option("--with-logs", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--keep-intermediate", type=click.Path(path_type=Path), default=None, help="Save intermediate DSL files to this folder.")
def generate_ff_benchmark_suite_command(
	in_folder: Path,
	out_base: Path,
	max_vars: int,
	circom_compiler: str | None,
	gnark_compiler: str | None,
	zokrates_compiler: str | None,
	circom_opt_levels: tuple[str, ...],
	max_out: int | None,
	skip_existing: bool,
	continue_on_error: bool,
	with_logs: bool,
	keep_intermediate: Path | None,
):
	"""Generate FF benchmark folders for Circom, Gnark, and ZoKrates from input SMT files."""
	try:
		generate_ff_benchmark_suite(
			in_folder=in_folder,
			out_base=out_base,
			max_vars=max_vars,
			circom_compiler=circom_compiler,
			gnark_compiler=gnark_compiler,
			zokrates_compiler=zokrates_compiler,
			circom_opt_levels=circom_opt_levels,
			max_out=max_out,
			skip_existing=skip_existing,
			continue_on_error=continue_on_error,
			with_logs=with_logs,
			keep_intermediate=keep_intermediate,
			log=click.echo,
		)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


@click.command(name="filter-ff-benchmarks")
@click.argument("in_folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--timeout", type=int, default=30, show_default=True, help="Solver timeout per call in seconds.")
@click.option("--max-iterations", type=int, default=5, show_default=True, help="Maximum number of disequality-augmentation rounds for a non-unique benchmark.")
@click.option("--stats-file", type=click.Path(path_type=Path), default=None, help="Path to a JSON file updated with running statistics every 100 benchmarks.")
def filter_ff_benchmarks_command(in_folder: Path, out_folder: Path, timeout: int, max_iterations: int, stats_file: Path | None):
	"""
	Filter a folder of QF_FF benchmarks to keep only uniquely satisfiable ones.

	UNSAT formulas are discarded. Non-unique formulas are augmented with
	per-variable disequality constraints against a second discovered model,
	then re-checked iteratively; if still non-unique they are discarded.

	IN_FOLDER: folder with .smt2 QF_FF files
	OUT_FOLDER: output folder for uniquely satisfiable .smt2 files
	"""
	try:
		filter_ff_benchmarks(
			in_folder,
			out_folder,
			timeout=timeout,
			max_iterations=max_iterations,
			stats_file=stats_file,
			log=click.echo,
		)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


@click.command(name="generate-poseidon-benchmarks")
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--count", "-n", type=int, default=10, show_default=True, help="Number of benchmarks to generate.")
@click.option("--seed", type=int, default=None, help="Random seed for reproducibility.")
@click.option("--min-rounds", type=int, default=1, show_default=True, help="Minimum number of Poseidon rounds.")
@click.option("--max-rounds", type=int, default=5, show_default=True, help="Maximum number of Poseidon rounds.")
def generate_poseidon_benchmarks_command(
    out_folder: Path,
    count: int,
    seed,
    min_rounds: int,
    max_rounds: int,
):
    """Generate unique-SAT finite-field benchmarks based on a Poseidon-like permutation.

    All benchmarks use the Circom prime (BN254 scalar field). Per benchmark,
    state width, S-box exponent, MDS matrix, and round constants are sampled
    independently. Each benchmark fixes a known output y and asks the solver to
    find the unique input x such that Poseidon(x) = y.

    OUT_FOLDER: directory where .smt2 files will be written.
    """
    try:
        from src.cli.benchmark_gen_cli.poseidon import generate_poseidon_benchmarks
        generate_poseidon_benchmarks(
            out_folder=out_folder,
            count=count,
            seed=seed,
            min_rounds=min_rounds,
            max_rounds=max_rounds,
            log=click.echo,
        )
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@click.command(name="sudoku17-to-smtlib2")
@click.argument("sudoku_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--start", type=int, default=1, show_default=True, help="1-based puzzle index to start from.")
@click.option("--max-out", type=int, default=None, help="Maximum number of puzzles to convert.")
def sudoku17_to_smtlib2_command(sudoku_file: Path, out_folder: Path, start: int, max_out: int | None):
	"""Convert Royle sudoku17 text file into SMT-LIB2 files."""
	try:
		sudoku17_to_smtlib2(sudoku_file, out_folder, start, max_out, log=click.echo)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()
