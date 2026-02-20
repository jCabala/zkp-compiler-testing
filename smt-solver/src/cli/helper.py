import json
import re
from random import Random
import random
import shutil
import subprocess
from datetime import datetime, UTC
from types import SimpleNamespace
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
from src.backends.noir.ir2noir import IR2NoirVisitor
from src.backends.noir.emitter import EmitVisitor as NoirEmitter
from src.smt_lib.prune import prune_formula, run_smt_solver_models
from third_party.yinyang.yinyang.src.parsing.Parse import parse_file
from third_party.yinyang.yinyang.src.mutators.SemanticFusion.SemanticFusion import SemanticFusion


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


def _sudoku_var_id(row: int, col: int, digit: int) -> int:
	"""
	Map (row, col, digit) in 1..9 to DIMACS variable id in 1..729.
	"""
	return 81 * (row - 1) + 9 * (col - 1) + digit


def _sudoku_cnf_from_line(puzzle: str) -> str:
	"""
	Build DIMACS CNF for a 9x9 Sudoku puzzle encoded as 81 chars.
	Accepted empty markers: '0' or '.'.
	"""
	puzzle = puzzle.strip()
	if len(puzzle) != 81:
		raise ValueError(f"Expected puzzle line of length 81, got {len(puzzle)}")
	if any(ch not in "0123456789." for ch in puzzle):
		raise ValueError("Puzzle contains invalid characters (expected digits, 0, or .)")

	clauses: list[list[int]] = []

	# 1) Each cell has exactly one digit
	for r in range(1, 10):
		for c in range(1, 10):
			# At least one
			clauses.append([_sudoku_var_id(r, c, d) for d in range(1, 10)])
			# At most one (pairwise)
			for d1 in range(1, 10):
				for d2 in range(d1 + 1, 10):
					clauses.append([-_sudoku_var_id(r, c, d1), -_sudoku_var_id(r, c, d2)])

	# 2) Each row has each digit exactly once
	for r in range(1, 10):
		for d in range(1, 10):
			clauses.append([_sudoku_var_id(r, c, d) for c in range(1, 10)])
			for c1 in range(1, 10):
				for c2 in range(c1 + 1, 10):
					clauses.append([-_sudoku_var_id(r, c1, d), -_sudoku_var_id(r, c2, d)])

	# 3) Each column has each digit exactly once
	for c in range(1, 10):
		for d in range(1, 10):
			clauses.append([_sudoku_var_id(r, c, d) for r in range(1, 10)])
			for r1 in range(1, 10):
				for r2 in range(r1 + 1, 10):
					clauses.append([-_sudoku_var_id(r1, c, d), -_sudoku_var_id(r2, c, d)])

	# 4) Each 3x3 box has each digit exactly once
	for br in (1, 4, 7):
		for bc in (1, 4, 7):
			cells = [(r, c) for r in range(br, br + 3) for c in range(bc, bc + 3)]
			for d in range(1, 10):
				clauses.append([_sudoku_var_id(r, c, d) for (r, c) in cells])
				for i in range(len(cells)):
					for j in range(i + 1, len(cells)):
						r1, c1 = cells[i]
						r2, c2 = cells[j]
						clauses.append([-_sudoku_var_id(r1, c1, d), -_sudoku_var_id(r2, c2, d)])

	# 5) Clues
	for idx, ch in enumerate(puzzle):
		if ch in ("0", "."):
			continue
		r = idx // 9 + 1
		c = idx % 9 + 1
		d = int(ch)
		clauses.append([_sudoku_var_id(r, c, d)])

	lines = [f"p cnf 729 {len(clauses)}"]
	lines.extend(" ".join(str(l) for l in clause) + " 0" for clause in clauses)
	return "\n".join(lines) + "\n"


def _all_assignments(nvars: int) -> list[tuple[bool, ...]]:
	return [tuple(bool((mask >> i) & 1) for i in range(nvars)) for mask in range(1 << nvars)]


def _lit_value(lit: int, assignment: tuple[bool, ...]) -> bool:
	idx = abs(lit) - 1
	val = assignment[idx]
	return val if lit > 0 else (not val)


def _clause_satisfied(clause: tuple[int, ...], assignment: tuple[bool, ...]) -> bool:
	return any(_lit_value(l, assignment) for l in clause)


def _random_clause_keep_target(rng: random.Random, nvars: int, target: tuple[bool, ...]) -> tuple[int, ...]:
	width = rng.randint(1, min(3, nvars))
	vars_chosen = rng.sample(range(1, nvars + 1), width)
	lits = [rng.choice([1, -1]) * v for v in vars_chosen]
	if not _clause_satisfied(tuple(lits), target):
		j = rng.randrange(len(lits))
		v = abs(lits[j])
		lits[j] = v if target[v - 1] else -v
	return tuple(lits)


def _build_unique_cnf(rng: random.Random, nvars: int) -> tuple[list[tuple[int, ...]], tuple[bool, ...]]:
	universe = _all_assignments(nvars)
	target = rng.choice(universe)
	remaining = {a for a in universe if a != target}
	clauses: list[tuple[int, ...]] = []
	seen: set[tuple[int, ...]] = set()

	attempts = 0
	while remaining:
		attempts += 1
		if attempts > 20000:
			raise RuntimeError("Could not construct a unique CNF in allotted attempts.")

		clause = _random_clause_keep_target(rng, nvars, target)
		if clause in seen:
			continue
		killed = {a for a in remaining if not _clause_satisfied(clause, a)}
		if not killed:
			continue

		seen.add(clause)
		clauses.append(clause)
		remaining.difference_update(killed)

	# Extra target-satisfying clauses for syntactic diversity
	for _ in range(rng.randint(0, 4)):
		clause = _random_clause_keep_target(rng, nvars, target)
		if clause not in seen:
			seen.add(clause)
			clauses.append(clause)

	return clauses, target


def _clauses_to_dimacs(nvars: int, clauses: list[tuple[int, ...]]) -> str:
	lines = [f"p cnf {nvars} {len(clauses)}"]
	lines.extend(" ".join(str(l) for l in c) + " 0" for c in clauses)
	return "\n".join(lines) + "\n"

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
				"--O2",
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

	Each input formula produces --variants outputs with different seeds.
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


@click.command(name="generate-unique-sat-benchmark")
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--count", type=int, default=1000, show_default=True, help="Number of SMT2 files to generate.")
@click.option("--nvars", type=int, default=5, show_default=True, help="Number of Boolean variables per formula.")
@click.option("--seed", type=int, default=42, show_default=True, help="Random seed.")
def generate_unique_sat_benchmark_command(out_folder: Path, count: int, nvars: int, seed: int):
	"""
	Generate a benchmark of uniquely satisfiable SMT-LIB2 formulas.
	"""
	try:
		if count <= 0:
			raise ValueError("--count must be > 0")
		if nvars <= 0:
			raise ValueError("--nvars must be > 0")

		out_folder.mkdir(parents=True, exist_ok=True)
		rng = random.Random(seed)
		generated = 0

		while generated < count:
			clauses, target = _build_unique_cnf(rng, nvars)

			dimacs = _clauses_to_dimacs(nvars, clauses)
			smt2 = cnf_string_to_smt2(dimacs)
			target_bits = "".join("1" if b else "0" for b in target)
			smt2 = f"; unique_target={target_bits}\n{smt2}"

			generated += 1
			out_file = out_folder / f"unique{nvars}_{generated:04d}.smt2"
			out_file.write_text(smt2)

		click.echo(f"✓ Generated {generated} unique SAT SMT-LIB2 file(s) in {out_folder}")
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


@click.command(name="sudoku17-to-smtlib2")
@click.argument("sudoku_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("out_folder", type=click.Path(path_type=Path))
@click.option("--start", type=int, default=1, show_default=True, help="1-based puzzle index to start from.")
@click.option("--max-out", type=int, default=None, help="Maximum number of puzzles to convert.")
def sudoku17_to_smtlib2_command(sudoku_file: Path, out_folder: Path, start: int, max_out: int | None):
	"""
	Convert Royle sudoku17 text file into SMT-LIB2 files via CNF->SMT utility.

	SUDOKU_FILE: Path to sudoku17.txt (one 81-char puzzle per line)
	OUT_FOLDER:  Output folder for generated .smt2 files
	"""
	try:
		if start <= 0:
			raise ValueError("--start must be >= 1")
		if max_out is not None and max_out <= 0:
			raise ValueError("--max-out must be > 0 when provided")

		out_folder.mkdir(parents=True, exist_ok=True)

		lines = [ln.strip() for ln in sudoku_file.read_text().splitlines() if ln.strip()]
		total = len(lines)
		begin = start - 1
		if begin >= total:
			click.echo(f"No puzzles to convert: start={start}, total={total}")
			return
		selected = lines[begin:]
		if max_out is not None:
			selected = selected[:max_out]

		converted = 0
		for i, puzzle in enumerate(selected, start=start):
			cnf = _sudoku_cnf_from_line(puzzle)
			smt2 = cnf_string_to_smt2(cnf)
			out_file = out_folder / f"royle17_{i:05d}.smt2"
			out_file.write_text(smt2)
			converted += 1

		click.echo(
			f"✓ Converted {converted} puzzle(s) from {sudoku_file} to SMT-LIB2 in {out_folder}"
		)
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()


def _extract_gnark_fragment_for_circuzz(go_source: str) -> str:
	start_idx = go_source.find("\ntype ")
	if start_idx == -1:
		start_idx = go_source.find("type ")
	if start_idx == -1:
		raise ValueError("Unable to locate Gnark type definition in generated source")

	end_idx = go_source.find("\nfunc main()")
	if end_idx == -1:
		raise ValueError("Unable to locate Gnark main() in generated source")

	fragment = go_source[start_idx:end_idx].strip()
	return fragment + "\n"


def _sanitize_noir_package_name(name: str) -> str:
	cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
	if not cleaned:
		cleaned = "noir_case"
	if cleaned[0].isdigit():
		cleaned = f"p_{cleaned}"
	return cleaned.lower()


def _write_noir_project(project_dir: Path, package_name: str, main_nr_source: str):
	src_dir = project_dir / "src"
	src_dir.mkdir(parents=True, exist_ok=True)
	(src_dir / "main.nr").write_text(main_nr_source)

	nargo_toml = project_dir / "Nargo.toml"
	nargo_toml.write_text(
		"\n".join(
			[
				"[package]",
				f'name = "{package_name}"',
				'type = "bin"',
				'authors = [""]',
				"",
				"[dependencies]",
				"",
			]
		)
	)


def _translate_smtlib2_to_dsl(smtlib2: str, dsl: str, output_format: str = "standalone") -> tuple[str, str]:
	# Parse SMT-LIB v2 to Circuit IR
	circuit_ir: Circuit = parse_smtlib2_core(smtlib2)

	if dsl == "circom":
		# Convert Circuit IR to Circom IR
		rng = Random(0)
		ir2circom_visitor = IR2CircomVisitorConstrainAssertions(
			constraint_assignment_probability=1,
			rng=rng,
		)
		circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)

		# Emit Circom code from Circom IR
		emitter = CircomEmitter()
		circom_source = emitter.emit(circom_ir)
		if output_format == "circuzz":
			circom_source = circom_source.replace("../circomlib/", "")
		return circom_source, ".circom"

	if dsl == "gnark":
		# Convert Circuit IR to Gnark IR
		ir2gnark_visitor = IR2GnarkVisitor(circuzz_compat=(output_format == "circuzz"))
		gnark_ir = ir2gnark_visitor.visit_circuit(circuit_ir)

		# Emit Gnark code from Gnark IR
		emitter = GnarkEmitter()
		gnark_source = emitter.emit(gnark_ir)
		if output_format == "circuzz":
			return _extract_gnark_fragment_for_circuzz(gnark_source), ".go"
		return gnark_source, ".go"

	if dsl == "noir":
		ir2noir_visitor = IR2NoirVisitor()
		noir_ast = ir2noir_visitor.visit_circuit(circuit_ir)

		emitter = NoirEmitter()
		return emitter.emit(noir_ast), ".nr"

	raise ValueError(f"Unsupported DSL: {dsl}")


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
	"""
	Translate SMT-LIB v2 core theory files into target DSL programs.

	IN_FOLDER: Path to folder containing .smt2 files
	OUT_FOLDER: Path to folder to store generated DSL files
	"""
	check_cmd_exists("z3")
	out_folder.mkdir(parents=True, exist_ok=True)
	smt2_files = list(in_folder.glob("*.smt2"))
	if not smt2_files:
		click.echo(f"No .smt2 files found in {in_folder}")
		return

	selected_files = smt2_files[:max_out] if max_out is not None else smt2_files
	converted_count = 0
	for smt2_file in selected_files:
		smtlib2 = smt2_file.read_text()
		dsl_code, extension = _translate_smtlib2_to_dsl(smtlib2, dsl, output_format=output_format)
		if output_format == "circuzz" and dsl == "noir":
			project_dir = out_folder / smt2_file.stem
			package_name = _sanitize_noir_package_name(smt2_file.stem)
			_write_noir_project(project_dir, package_name, dsl_code)
			out_file = project_dir / "src" / "main.nr"
		else:
			out_file = out_folder / f"{smt2_file.stem}{extension}"
			out_file.write_text(dsl_code)
		click.echo(f"Translating {smt2_file} -> {out_file}")
		converted_count += 1

	click.echo(f"✓ Converted {converted_count} files to {dsl} ({output_format}) in {out_folder}")


@click.command(name="fuse-smt-to-dsl")
@click.argument("in_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("out_dir", type=click.Path(path_type=Path))
@click.option("--dsl", type=click.Choice(["circom", "gnark", "noir"]), required=True, help="Target DSL for generated programs.")
@click.option("--seed", type=int, default=0, show_default=True, help="Random seed for reproducible fusion generation.")
@click.option("--num-outputs", type=int, required=True, help="Number of fused outputs to generate.")
@click.option(
	"--config",
	type=click.Path(exists=True, dir_okay=False, path_type=Path),
	default=Path("third_party/yinyang/yinyang/config/fusion_functions.txt"),
	show_default=True,
	help="Path to YinYang fusion function config.",
)
@click.option(
	"--oracle",
	type=click.Choice(["sat", "unsat"]),
	default="sat",
	show_default=True,
	help="Fusion oracle passed to SemanticFusion.",
)
@click.option(
	"--max-attempts",
	type=int,
	default=None,
	help="Maximum attempts before aborting (default: 50 * num-outputs).",
)
@click.option(
	"--max-models",
	type=int,
	default=1,
	show_default=True,
	help="Maximum number of SAT models to store per fused output.",
)
@click.option(
	"--format",
	"output_format",
	type=click.Choice(["standalone", "circuzz"]),
	default="standalone",
	show_default=True,
	help="Output layout/format profile.",
)
def fuse_smt_to_dsl_command(
	in_dir: Path,
	out_dir: Path,
	dsl: str,
	seed: int,
	num_outputs: int,
	config: Path,
	oracle: str,
	max_attempts: int | None,
	max_models: int,
	output_format: str,
):
	"""
	Generate fused SMT programs using local YinYang SemanticFusion and emit paired DSL files.

	IN_DIR:  Folder with input SMT seed programs (.smt2)
	OUT_DIR: Folder where paired outputs will be written
	"""
	try:
		if num_outputs <= 0:
			raise ValueError("--num-outputs must be > 0")
		if max_models <= 0:
			raise ValueError("--max-models must be > 0")

		seed_files = sorted(in_dir.rglob("*.smt2"))
		if len(seed_files) < 2:
			raise ValueError(f"Need at least 2 .smt2 seed files in {in_dir}, found {len(seed_files)}")

		out_smt_dir = out_dir / "smt2"
		out_dsl_dir = out_dir / "dsl"
		out_sol_dir = out_dir / "solutions"
		out_smt_dir.mkdir(parents=True, exist_ok=True)
		out_dsl_dir.mkdir(parents=True, exist_ok=True)
		out_sol_dir.mkdir(parents=True, exist_ok=True)
		config_copy_path = out_dir / f"yinyang_config{config.suffix or '.txt'}"
		shutil.copy2(config, config_copy_path)

		rng = random.Random(seed)
		args = SimpleNamespace(config=str(config), oracle=oracle)
		limit = max_attempts if max_attempts is not None else 50 * num_outputs
		if limit <= 0:
			raise ValueError("--max-attempts must be > 0 when provided")

		manifest_rows: list[dict[str, object]] = []
		seed_inputs_cache: dict[Path, list[str]] = {}
		generated = 0
		attempts = 0
		skipped = 0
		failed = 0

		while generated < num_outputs and attempts < limit:
			attempts += 1
			left, right = rng.sample(seed_files, 2)
			script1, _ = parse_file(str(left), silent=True)
			script2, _ = parse_file(str(right), silent=True)
			if script1 is None or script2 is None:
				failed += 1
				continue

			# Seed global random because SemanticFusion uses random module internally.
			random.seed(rng.randint(0, 2**31 - 1))
			mutator = SemanticFusion(script1, script2, args)
			mutant, success, skip_seed = mutator.mutate()
			if not success or skip_seed:
				skipped += 1
				continue

			smt_text = str(mutant)
			try:
				dsl_text, extension = _translate_smtlib2_to_dsl(smt_text, dsl, output_format=output_format)
			except Exception:
				failed += 1
				continue

			solve_result, solve_models = run_smt_solver_models(smt_text, solver="z3", max_models=max_models)
			if solve_result != "sat" or not solve_models:
				failed += 1
				continue

			if left not in seed_inputs_cache:
				left_circuit = parse_smtlib2_core(left.read_text())
				seed_inputs_cache[left] = [v.name for v in left_circuit.inputs]
			if right not in seed_inputs_cache:
				right_circuit = parse_smtlib2_core(right.read_text())
				seed_inputs_cache[right] = [v.name for v in right_circuit.inputs]

			model_payloads: list[dict[str, object]] = []
			for model in solve_models:
				assignments: dict[str, object] = {}
				for name in seed_inputs_cache[left]:
					prefixed = f"scr1_{name}"
					val = model.get(prefixed)
					if val is not None:
						assignments[prefixed] = val
				for name in seed_inputs_cache[right]:
					prefixed = f"scr2_{name}"
					val = model.get(prefixed)
					if val is not None:
						assignments[prefixed] = val
				model_payloads.append(
					{
						"assignments": assignments,
						"fused_assignments": {
							name: val for name, val in model.items() if name.endswith("_fused")
						},
					}
				)

			generated += 1
			stem = f"fused_{generated:04d}"
			smt_path = out_smt_dir / f"{stem}.smt2"
			if output_format == "circuzz" and dsl == "noir":
				dsl_project_dir = out_dsl_dir / stem
				package_name = _sanitize_noir_package_name(stem)
				_write_noir_project(dsl_project_dir, package_name, dsl_text)
				dsl_path = dsl_project_dir / "src" / "main.nr"
			else:
				dsl_path = out_dsl_dir / f"{stem}{extension}"
				dsl_path.write_text(dsl_text)
			solution_path = out_sol_dir / f"{stem}.json"
			smt_path.write_text(smt_text)
			solution_payload = {
				"result": solve_result,
				"seed_left": str(left),
				"seed_right": str(right),
				"max_models_requested": max_models,
				"model_count": len(model_payloads),
				"models": model_payloads,
			}
			# Backward compatibility: keep first model flattened at top-level.
			solution_payload["assignments"] = model_payloads[0]["assignments"]
			solution_payload["fused_assignments"] = model_payloads[0]["fused_assignments"]
			solution_path.write_text(json.dumps(solution_payload, indent=2))
			manifest_rows.append(
				{
					"index": generated,
					"attempt": attempts,
					"seed_left": str(left),
					"seed_right": str(right),
					"smt_path": str(smt_path),
					"dsl_path": str(dsl_path),
					"solution_path": str(solution_path),
				}
			)
			click.echo(f"[{generated}/{num_outputs}] {left.name} + {right.name} -> {dsl_path.name}")

		manifest = {
			"dsl": dsl,
			"format": output_format,
			"seed": seed,
			"oracle": oracle,
			"config": str(config),
			"config_copy": str(config_copy_path),
			"in_dir": str(in_dir),
			"out_dir": str(out_dir),
			"solutions_dir": str(out_sol_dir),
			"solution_solver": "z3",
			"max_models_per_output": max_models,
			"num_outputs_requested": num_outputs,
			"num_outputs_generated": generated,
			"attempts": attempts,
			"skipped": skipped,
			"failed": failed,
			"generated_at": datetime.now(UTC).isoformat(),
			"outputs": manifest_rows,
		}
		(out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

		if generated < num_outputs:
			raise RuntimeError(
				f"Generated {generated}/{num_outputs} before reaching max attempts ({limit}). "
				f"See {out_dir / 'manifest.json'}."
			)

		click.echo(f"✓ Generated {generated} fused SMT + {dsl} ({output_format}) program pairs in {out_dir}")
	except Exception as e:
		click.echo(f"✗ Error: {e}", err=True)
		raise click.Abort()
