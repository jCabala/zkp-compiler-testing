from pathlib import Path
import click

from src.cli.benchmark_gen_cli.bool_to_ff import generate_ff_benchmarks
from src.cli.benchmark_gen_cli.sudoku import sudoku17_to_smtlib2


@click.command(name="bool-smt-to-ff")
@click.argument("in_folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--dsl", type=click.Choice(["circom", "gnark"]), required=True, help="Compiler backend to use.")
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
