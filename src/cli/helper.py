import json
from random import Random
import shutil
import subprocess
from pathlib import Path
import click
from src.backends.circom.r1cs import get_r1cs_json
from src.smt_lib import cnf_string_to_smt2
from src.smt_lib.zk_ir import Circuit
from src.backends.circom.emitter import EmitVisitor as CircomEmitter
from src.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
from src.smt_lib.smt_lib_parser import parse_smtlib2_core
from src.backends.gnark.ir2gnark import IR2GnarkVisitor
from src.backends.gnark.emitter import EmitVisitor as GnarkEmitter


def check_cmd_exists(cmd: str):
	"""Exit with a clear error if a required command is missing."""
	if shutil.which(cmd) is None:
		click.echo(f"✗ Error: '{cmd}' not found in PATH. Please install it first.", err=True)
		raise click.Abort()

def run(cmd, cwd=None):
	"""Run a subprocess command with basic logging and error handling."""
	click.echo(f"\n>>> Running: {' '.join(str(c) for c in cmd)}")
	try:
		subprocess.run(cmd, cwd=cwd, check=True)
	except subprocess.CalledProcessError as e:
		click.echo(f"\n✗ Command failed with exit code {e.returncode}", err=True)
		raise click.Abort()

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

		# Determine output path
		if output is None:
			output = circom_path.with_suffix('.r1cs.json')

		# pretty-print
		r1cs_data = json.loads(r1cs_json_str)
		r1cs_json_str = json.dumps(r1cs_data, indent=2)

		# Write to file
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
	--ptau:      Path to the powersOfTau .ptau file (option; defaults to ptau10)

	Returns (via generated files inside the output directory):
	  - <name>.r1cs .......... compiled constraint system
	  - <name>.wasm .......... witness generator
	  - <name>.wtns .......... witness from input.json
	  - <name>_0000.zkey ..... initial proving key
	  - <name>_final.zkey .... final proving key after contribution
	  - <name>_verification_key.json .. verification key
	  - <name>_proof.json .... zk-SNARK proof
	  - <name>_public.json ... public signals

	The command does not return a Python value;
	instead it creates these artifacts and verifies the proof.
	A successful run ends with '✓ Proof verified successfully!'.
	"""
	try:
		# Resolve paths
		circom_path = circom_path.resolve()
		input_json = input_json.resolve()
		ptau = ptau.resolve()

		circuit_name = circom_path.stem

		if outdir is None:
			build_dir = Path(f"build_{circuit_name}")
		else:
			build_dir = outdir

		build_dir.mkdir(parents=True, exist_ok=True)

		# Check dependencies
		click.echo("Checking dependencies...")
		check_cmd_exists("circom")
		check_cmd_exists("node")
		check_cmd_exists("snarkjs")

		click.echo("\n========================================")
		click.echo(f"1. Compiling circuit: {circom_path}")
		click.echo("========================================")

		# circom <file> --r1cs --wasm --sym -o <build_dir>
		run(
			[
				"circom",
				str(circom_path),
				"--r1cs",
				"--wasm",
				"--sym",
				"--json",
				"-o",
				str(build_dir),
			]
		)

		r1cs_file = build_dir / f"{circuit_name}.r1cs"
		sym_file = build_dir / f"{circuit_name}.sym"
		witness_file = build_dir / f"{circuit_name}.wtns"
		zkey_0 = build_dir / f"{circuit_name}_0000.zkey"
		zkey_final = build_dir / f"{circuit_name}_final.zkey"
		vkey_file = build_dir / f"{circuit_name}_verification_key.json"
		proof_file = build_dir / f"{circuit_name}_proof.json"
		public_file = build_dir / f"{circuit_name}_public.json"

		js_dir = build_dir / f"{circuit_name}_js"
		generate_witness_js = js_dir / "generate_witness.js"
		wasm_file = js_dir / f"{circuit_name}.wasm"

		if not generate_witness_js.is_file():
			click.echo(f"✗ Error: witness generator not found at {generate_witness_js}", err=True)
			raise click.Abort()

		click.echo("\nGenerated files:")
		click.echo(f"  - {r1cs_file}")
		click.echo(f"  - {wasm_file}")
		click.echo(f"  - {sym_file}")
		click.echo(f"  - {js_dir}/")

		click.echo("\n========================================")
		click.echo(f"2. Generating witness from: {input_json}")
		click.echo("========================================")

		# node <js_dir>/generate_witness.js <wasm> <input.json> <witness.wtns>
		run(
			[
				"node",
				str(generate_witness_js),
				str(wasm_file),
				str(input_json),
				str(witness_file),
			]
		)

		click.echo(f"\n✓ Witness generated: {witness_file}")

		click.echo("\n========================================")
		click.echo("3. Groth16 setup")
		click.echo("========================================")

		# snarkjs groth16 setup <circuit.r1cs> <ptau> <circuit_0000.zkey>
		run(
			[
				"snarkjs",
				"groth16",
				"setup",
				str(r1cs_file),
				str(ptau),
				str(zkey_0),
			]
		)

		click.echo(f"\n✓ Initial zkey created: {zkey_0}")

		click.echo("\n========================================")
		click.echo("4. Contributing to phase 2 (zkey)")
		click.echo("========================================")

		# snarkjs zkey contribute <0000.zkey> <final.zkey> --name="First contribution" -v
		run(
			[
				"snarkjs",
				"zkey",
				"contribute",
				str(zkey_0),
				str(zkey_final),
				"--name=First contribution",
				"-v",
			]
		)

		click.echo(f"\n✓ Final zkey: {zkey_final}")

		click.echo("\n========================================")
		click.echo("5. Exporting verification key")
		click.echo("========================================")

		# snarkjs zkey export verificationkey <final.zkey> <verification_key.json>
		run(
			[
				"snarkjs",
				"zkey",
				"export",
				"verificationkey",
				str(zkey_final),
				str(vkey_file),
			]
		)

		click.echo(f"\n✓ Verification key: {vkey_file}")

		click.echo("\n========================================")
		click.echo("6. Generating proof")
		click.echo("========================================")

		# snarkjs groth16 prove <final.zkey> <witness.wtns> <proof.json> <public.json>
		run(
			[
				"snarkjs",
				"groth16",
				"prove",
				str(zkey_final),
				str(witness_file),
				str(proof_file),
				str(public_file),
			]
		)

		click.echo(f"\n✓ Proof: {proof_file}")
		click.echo(f"✓ Public signals: {public_file}")

		click.echo("\n========================================")
		click.echo("7. Verifying proof")
		click.echo("========================================")

		# snarkjs groth16 verify <verification_key.json> <public.json> <proof.json>
		run(
			[
				"snarkjs",
				"groth16",
				"verify",
				str(vkey_file),
				str(public_file),
				str(proof_file),
			]
		)

		click.echo("\n✅ Proof verified successfully!")

	except click.Abort:
		# Already logged, just propagate
		raise
	except Exception as e:
		click.echo(f"✗ Unexpected error: {e}", err=True)
		raise click.Abort()

# --------------------------- CNF to SMT-LIB2 Batch Command ----------------------------------
@click.command(name="cnf-to-smtlib2")
@click.argument('in_folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('out_folder', type=click.Path(path_type=Path))
def cnf_to_smtlib2_command(in_folder: Path, out_folder: Path):
	"""
	Translate all .cnf files in IN_FOLDER to SMT-LIB v2 format and store them in OUT_FOLDER.

	IN_FOLDER: Path to folder containing .cnf files
	OUT_FOLDER: Path to folder to store .smt2 files
	"""
	try:
		check_cmd_exists("z3")
		out_folder.mkdir(parents=True, exist_ok=True)
		cnf_files = list(in_folder.glob("*.cnf"))
		if not cnf_files:
			click.echo(f"No .cnf files found in {in_folder}")
			return
		for cnf_file in cnf_files:
			out_file = out_folder / (cnf_file.stem + ".smt2")
			click.echo(f"Translating {cnf_file} -> {out_file}")
			# Z3 translation: z3 -dimacs input.cnf -smt2 > output.smt2
			out_file.write_text(cnf_string_to_smt2(cnf_file.read_text()))
		click.echo(f"✓ Converted {len(cnf_files)} files to SMT-LIB v2 in {out_folder}")
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


@click.command(name="smtlib2-to-circom")
@click.argument('in_folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('out_folder', type=click.Path(path_type=Path))
def translate_to_circom_command(in_folder: Path, out_folder: Path):
	"""
	Translate an SMT-LIB v2 core theory string into .circom files.

	IN_FOLDER: Path to folder containing .smt2 files
	OUT_FOLDER: Path to folder to store .circom files
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

	check_cmd_exists("z3")
	out_folder.mkdir(parents=True, exist_ok=True)
	smt2_files = list(in_folder.glob("*.smt2"))
	if not smt2_files:
		click.echo(f"No .smt2 files found in {in_folder}")
		return
	for smt2_file in smt2_files:
		out_file = out_folder / (smt2_file.stem + ".circom")
		click.echo(f"Translating {smt2_file} -> {out_file}")
		smtlib2 = smt2_file.read_text()
		circom_code = smtlib2_to_circom(smtlib2)
		out_file.write_text(circom_code)
	click.echo(f"✓ Converted {len(smt2_files)} files to Circom in {out_folder}")

@click.command(name="smtlib2-to-gnark")
@click.argument('in_folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('out_folder', type=click.Path(path_type=Path))
@click.option('--max-out', type=int, default=None, help="Maximum number of files to convert.")
def translate_to_gnark_command(in_folder: Path, out_folder: Path, max_out: int | None):
	"""
	Translate an SMT-LIB v2 core theory string into .go files for Gnark.

	IN_FOLDER: Path to folder containing .smt2 files
	OUT_FOLDER: Path to folder to store .go files
	"""

	def smtlib2_to_gnark(smtlib2: str) -> str:
		# Parse SMT-LIB v2 to Circuit IR
		circuit_ir: Circuit = parse_smtlib2_core(smtlib2)

		# Convert Circuit IR to Gnark IR
		ir2gnark_visitor = IR2GnarkVisitor()
		gnark_ir = ir2gnark_visitor.visit_circuit(circuit_ir)

		# Emit Gnark code from Gnark IR
		emitter = GnarkEmitter()
		gnark_code = emitter.emit(gnark_ir)

		return gnark_code
		
		
	check_cmd_exists("z3")
	out_folder.mkdir(parents=True, exist_ok=True)
	smt2_files = list(in_folder.glob("*.smt2"))
	if not smt2_files:
		click.echo(f"No .smt2 files found in {in_folder}")
		return
	for smt2_file in smt2_files[:max_out] if max_out is not None else smt2_files:
		out_file = out_folder / (smt2_file.stem + ".go")
		click.echo(f"Translating {smt2_file} -> {out_file}")
		smtlib2 = smt2_file.read_text()
		gnark_code = smtlib2_to_gnark(smtlib2)
		out_file.write_text(gnark_code)
	click.echo(f"✓ Converted {len(smt2_files)} files to Gnark in {out_folder}")
