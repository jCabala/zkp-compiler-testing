import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4
from src.smt_lib.smt_lib_parser import parse_smtlib2_core
from src.smt_lib.zk_ir import Circuit
from src.backends.gnark.ir2gnark import IR2GnarkVisitor
from src.backends.gnark.emitter import EmitVisitor as GnarkEmitter
from src.r1cs.solve import solve_r1cs
from src.r1cs.optimization.optimize import optimize_r1cs
from src.cli.solver_cli.common import log, solution_to_str, run_picus

_GO_CACHE_CLEAN_INTERVAL = 1000
_GO_CACHE_COUNTER_FILE = ".go_run_count"


def maybe_clean_go_cache() -> None:
	"""Periodically run `go clean -cache` to prevent unbounded GOCACHE growth.

	Each `go run` on a unique circuit adds a cache entry that is never reused.
	Because cli.py is a short-lived subprocess per circuit, state is persisted
	in a counter file inside GOCACHE so it survives across invocations.
	"""
	gocache = os.environ.get("GOCACHE")
	if not gocache:
		return
	counter_path = Path(gocache) / _GO_CACHE_COUNTER_FILE
	try:
		count = int(counter_path.read_text()) if counter_path.exists() else 0
		count += 1
		counter_path.write_text(str(count))
		if count % _GO_CACHE_CLEAN_INTERVAL == 0:
			subprocess.run(["go", "clean", "-cache"], capture_output=True)
			counter_path.write_text("0")
	except OSError:
		pass  # non-fatal: cache grows a bit more until next successful clean


def smtlib2_to_gnark(smtlib2: str, solver: str = "z3") -> str:
	"""Parse SMT-LIB v2 and convert to Gnark Go code."""
	circuit_ir: Circuit = parse_smtlib2_core(smtlib2, solver=solver)
	ir2gnark_visitor = IR2GnarkVisitor()
	gnark_ir = ir2gnark_visitor.visit_circuit(circuit_ir)
	emitter = GnarkEmitter()
	return emitter.emit(gnark_ir)


def resolve_hints_for_gnark(sr1cs_str: str, hint_model: dict) -> dict[int, int]:
	"""Map SMT variable names to Gnark wire indices using SR1CS labels."""
	label_re = re.compile(r'^\s*\(label\s+(\d+)\s+(.+?)\s*\)\s*$')
	name_to_wire = {}
	for line in sr1cs_str.splitlines():
		m = label_re.match(line)
		if m:
			wire_idx = int(m.group(1))
			name = m.group(2).strip().strip('"')
			name_to_wire[name] = wire_idx

	hints = {}
	for var_name, value in hint_model.items():
		if var_name in name_to_wire:
			int_val = int(value) if isinstance(value, bool) else value
			hints[name_to_wire[var_name]] = int_val
	return hints


def solve_gnark(gnark_path: Path, with_model: bool, with_logs: bool, solver: str, tmp_dir: Path, hint_model: dict | None = None, solving_timeout: int | None = None) -> str:
	"""Compile a GNARK (Go) circuit, export its R1CS, and solve with an SMT solver. Returns 'sat' or 'unsat'."""
	from src.backends.gnark.r1cs import get_r1cs_sr1cs, parse_sr1cs

	log(f"Compiling GNARK file: {gnark_path}...", with_logs=with_logs)
	r1cs_sr1cs_str = get_r1cs_sr1cs(gnark_path)
	maybe_clean_go_cache()

	wire_hints = {}
	if hint_model:
		wire_hints = resolve_hints_for_gnark(r1cs_sr1cs_str, hint_model)
		log(f"Resolved {len(wire_hints)} hint wire assignments", with_logs=with_logs)

	if solver == "picus":
		log("Solving R1CS using Picus...", with_logs)
		tmp_dir.mkdir(parents=True, exist_ok=True)
		tmp_sr1cs_path = tmp_dir / f"temp-{uuid4()}.sr1cs"
		try:
			tmp_sr1cs_path.write_text(r1cs_sr1cs_str)
			return run_picus(tmp_sr1cs_path, hints=wire_hints or None, solving_timeout=solving_timeout)
		finally:
			if tmp_sr1cs_path.exists():
				tmp_sr1cs_path.unlink()

	log("Parsing R1CS SR1CS...", with_logs)
	r1cs = parse_sr1cs(r1cs_sr1cs_str)

	if wire_hints:
		r1cs.hints = wire_hints

	log("Optimizing R1CS...", with_logs)
	r1cs = optimize_r1cs(r1cs, with_logs=with_logs)

	log("Solving R1CS using a SMT solver...", with_logs)
	solution = solve_r1cs(r1cs, backend=solver, with_logs=with_logs, solving_timeout=solving_timeout)
	return solution_to_str(solution)
