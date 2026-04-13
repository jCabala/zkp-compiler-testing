import json
import shutil
from pathlib import Path
import click
from src.backends.circom.r1cs import get_r1cs_json
from src.smt_lib import cnf_string_to_smt2
from src.smt_lib.prune import prune_formula
from src.cli.helper_tools_cli.generate_proof import generate_proof, ProofGenerationError
from src.cli.helper_tools_cli.unique_sat_benchmark import generate_unique_sat_benchmarks
from src.cli.helper_tools_cli.translate_dsl import translate_smtlib2_folder


# --------------------------- Export R1CS Command ----------------------------------
@click.command()
@click.argument('circom_path', type=click.Path(exists=True, path_type=Path))
@click.option(
	'--output',
	'-o',
	type=click.Path(path_type=Path),
	help='Output path for the R1CS JSON file (default: <circuit_name>.r1cs.json)',
)
def export_r1cs_command(circom_path: Path, output: Path):
	"""
	Compile a Circom circuit and export its R1CS representation as JSON.

	CIRCOM_PATH: Path to the .circom file
	"""
	try:
		click.echo(f"Compiling {circom_path}...")
		r1cs_json_str = get_r1cs_json(circom_path)

		if output is None:
			output = circom_path.with_suffix('.r1cs.json')

		r1cs_data = json.loads(r1cs_json_str)
		r1cs_json_str = json.dumps(r1cs_data, indent=2)

		output.write_text(r1cs_json_str)

		click.echo(f"✓ R1CS JSON saved to: {output}")
		click.echo(f"  File size: {output.stat().st_size} bytes")

	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


# --------------------------- Generate Proof Command ----------------------------------
@click.command(name="generate-proof")
@click.argument('circom_path', type=click.Path(exists=True, path_type=Path))
@click.argument('input_json', type=click.Path(exists=True, path_type=Path))
@click.option(
	'--ptau',
	type=click.Path(exists=True, path_type=Path),
	default=Path("data/ptau10.ptau"),
	show_default=True,
	help='Path to the powersOfTau .ptau file',
)
@click.option(
	'--outdir',
	'-o',
	type=click.Path(path_type=Path),
	help='Output directory (default: build_<circuit_name>)',
)
def generate_proof_command(circom_path: Path, input_json: Path, ptau: Path, outdir: Path | None):
	"""
	Compile a Circom circuit and generate a Groth16 proof using snarkjs.

	CIRCOM_PATH: Path to the .circom file
	INPUT_JSON:  Path to the input.json file
	"""
	try:
		generate_proof(circom_path, input_json, ptau, outdir, log=click.echo)
	except ProofGenerationError as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


# --------------------------- CNF to SMT-LIB2 Batch Command ----------------------------------
@click.command(name="cnf-to-smtlib2")
@click.argument('in_folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('out_folder', type=click.Path(path_type=Path))
def cnf_to_smtlib2_command(in_folder: Path, out_folder: Path):
	"""
	Translate all .cnf files in IN_FOLDER to SMT-LIB v2 format and store them in OUT_FOLDER.
	"""
	try:
		if shutil.which("z3") is None:
			click.echo("✗ Error: 'z3' not found in PATH.", err=True)
			raise click.Abort()
		out_folder.mkdir(parents=True, exist_ok=True)
		cnf_files = list(in_folder.glob("*.cnf"))
		if not cnf_files:
			click.echo(f"No .cnf files found in {in_folder}")
			return
		for cnf_file in cnf_files:
			out_file = out_folder / (cnf_file.stem + ".smt2")
			click.echo(f"Translating {cnf_file} -> {out_file}")
			out_file.write_text(cnf_string_to_smt2(cnf_file.read_text()))
		click.echo(f"✓ Converted {len(cnf_files)} files to SMT-LIB v2 in {out_folder}")
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


# --------------------------- Prune SMT-LIB2 Folder Command ----------------------------------
@click.command(name="prune-smtlib2-folder")
@click.argument("in_folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--k", type=int, required=True, help="Keep k variables in each pruned output.")
@click.option("--variants", type=int, default=1, show_default=True, help="How many pruned variants to output per input formula.")
@click.option("--seed", type=int, default=0, show_default=True, help="Base random seed. Variant i uses seed+i.")
@click.option("--solver", type=click.Choice(["z3", "cvc5"]), default="z3", show_default=True, help="Solver used by pruning.")
def prune_smtlib2_folder_command(in_folder: Path, out_folder: Path, k: int, variants: int, seed: int, solver: str):
	"""
	Prune all .smt2 files in IN_FOLDER and write pruned variants to OUT_FOLDER.
	"""
	try:
		if k <= 0:
			raise ValueError("--k must be > 0")
		if variants <= 0:
			raise ValueError("--variants must be > 0")

		out_folder.mkdir(parents=True, exist_ok=True)
		smt2_files = sorted(in_folder.glob("*.smt2"))
		if not smt2_files:
			click.echo(f"No .smt2 files found in {in_folder}")
			return

		written = 0
		for smt2_file in smt2_files:
			content = smt2_file.read_text()
			for i in range(variants):
				variant_seed = seed + i
				pruned_content, metadata = prune_formula(
					content,
					k=k,
					solver=solver,
					seed=variant_seed,
					prefer_fused_pairs=False,
				)
				if not metadata.get("pruned", False):
					click.echo(
						f"Skipping {smt2_file.name} variant {i + 1}/{variants}: "
						f"{metadata.get('reason', 'pruning skipped')}"
					)
					continue

				out_file = out_folder / f"{smt2_file.stem}--prune{k}--seed{variant_seed}.smt2"
				out_file.write_text(pruned_content)
				written += 1

		click.echo(
			f"✓ Wrote {written} pruned SMT-LIB2 file(s) "
			f"from {len(smt2_files)} input file(s) to {out_folder}"
		)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


# --------------------------- Generate Unique SAT Benchmark Command ----------------------------------
@click.command(name="generate-unique-sat-benchmark")
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--count", type=int, default=1000, show_default=True, help="Number of SMT2 files to generate.")
@click.option("--nvars", type=int, default=5, show_default=True, help="Number of Boolean variables per formula.")
@click.option("--seed", type=int, default=42, show_default=True, help="Random seed.")
def generate_unique_sat_benchmark_command(out_folder: Path, count: int, nvars: int, seed: int):
	"""Generate a benchmark of uniquely satisfiable SMT-LIB2 formulas."""
	try:
		generate_unique_sat_benchmarks(out_folder, count, nvars, seed, log=click.echo)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


# --------------------------- Translate to DSL Command ----------------------------------
@click.command(name="smt-to-dsl")
@click.argument('in_folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('out_folder', type=click.Path(path_type=Path))
@click.option("--dsl", type=click.Choice(["circom", "gnark", "noir"]), required=True, help="Target DSL for generated programs.")
@click.option('--max-out', type=int, default=None, help="Maximum number of files to convert.")
@click.option(
	"--format",
	"output_format",
	type=click.Choice(["standalone", "circuzz"]),
	default="standalone",
	show_default=True,
	help="Output layout/format profile.",
)
def translate_to_dsl_command(in_folder: Path, out_folder: Path, dsl: str, max_out: int | None, output_format: str):
	"""Translate SMT-LIB v2 core theory files into target DSL programs."""
	try:
		if shutil.which("z3") is None:
			click.echo("✗ Error: 'z3' not found in PATH.", err=True)
			raise click.Abort()
		translate_smtlib2_folder(in_folder, out_folder, dsl, max_out, output_format, log=click.echo)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()
