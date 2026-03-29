import shutil
import subprocess
from pathlib import Path


class ProofGenerationError(Exception):
	pass


def _check_cmd(cmd: str):
	if shutil.which(cmd) is None:
		raise ProofGenerationError(f"'{cmd}' not found in PATH. Please install it first.")


def _run(cmd, cwd=None, log=print):
	log(f"\n>>> Running: {' '.join(str(c) for c in cmd)}")
	result = subprocess.run(cmd, cwd=cwd)
	if result.returncode != 0:
		raise ProofGenerationError(f"Command failed with exit code {result.returncode}")


def generate_proof(circom_path: Path, input_json: Path, ptau: Path, outdir: Path | None = None, log=print):
	"""
	Compile a Circom circuit and generate a Groth16 proof using snarkjs.

	Creates these artifacts in the output directory:
	  - <name>.r1cs, <name>.wasm, <name>.wtns
	  - <name>_0000.zkey, <name>_final.zkey
	  - <name>_verification_key.json
	  - <name>_proof.json, <name>_public.json
	"""
	circom_path = circom_path.resolve()
	input_json = input_json.resolve()
	ptau = ptau.resolve()

	circuit_name = circom_path.stem
	build_dir = outdir if outdir is not None else Path(f"build_{circuit_name}")
	build_dir.mkdir(parents=True, exist_ok=True)

	_check_cmd("circom")
	_check_cmd("node")
	_check_cmd("snarkjs")

	log(f"\n1. Compiling circuit: {circom_path}")
	_run(["circom", str(circom_path), "--r1cs", "--wasm", "--sym", "--json", "--O2", "-o", str(build_dir)], log=log)

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
		raise ProofGenerationError(f"Witness generator not found at {generate_witness_js}")

	log(f"\nGenerated files: {r1cs_file}, {wasm_file}, {sym_file}")

	log(f"\n2. Generating witness from: {input_json}")
	_run(["node", str(generate_witness_js), str(wasm_file), str(input_json), str(witness_file)], log=log)
	log(f"Witness generated: {witness_file}")

	log("\n3. Groth16 setup")
	_run(["snarkjs", "groth16", "setup", str(r1cs_file), str(ptau), str(zkey_0)], log=log)
	log(f"Initial zkey created: {zkey_0}")

	log("\n4. Contributing to phase 2 (zkey)")
	_run(["snarkjs", "zkey", "contribute", str(zkey_0), str(zkey_final), "--name=First contribution", "-v"], log=log)
	log(f"Final zkey: {zkey_final}")

	log("\n5. Exporting verification key")
	_run(["snarkjs", "zkey", "export", "verificationkey", str(zkey_final), str(vkey_file)], log=log)
	log(f"Verification key: {vkey_file}")

	log("\n6. Generating proof")
	_run(["snarkjs", "groth16", "prove", str(zkey_final), str(witness_file), str(proof_file), str(public_file)], log=log)
	log(f"Proof: {proof_file}")
	log(f"Public signals: {public_file}")

	log("\n7. Verifying proof")
	_run(["snarkjs", "groth16", "verify", str(vkey_file), str(public_file), str(proof_file)], log=log)
	log("Proof verified successfully!")
