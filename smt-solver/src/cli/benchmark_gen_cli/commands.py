from pathlib import Path
import click

from src.cli.benchmark_gen_cli.bool_to_ff import generate_ff_benchmarks, generate_ff_benchmark_suite
from src.cli.benchmark_gen_cli.sudoku import sudoku17_to_smtlib2


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
