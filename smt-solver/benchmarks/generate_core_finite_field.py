#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

from src.cli.benchmark_gen_cli.bool_to_ff import convert_bool_smt_to_ff


@dataclass(frozen=True)
class BackendSpec:
	dsl: str
	opt_level: str
	label: str
	compiler: str | None


BACKEND_SPECS = (
	BackendSpec(dsl="circom", opt_level="O2", label="circom_O2", compiler=None),
	BackendSpec(dsl="circom", opt_level="O1", label="circom_O1", compiler=None),
	BackendSpec(dsl="zokrates", opt_level="O2", label="zokrates", compiler=None),
)

DEFAULT_CORE_DIR = Path(__file__).resolve().parent / "core"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "finite-field"


def collect_core_files(core_dir: Path) -> list[Path]:
	return sorted(core_dir.rglob("*.smt2"))


def assign_backends(core_files: list[Path]) -> list[tuple[Path, BackendSpec]]:
	total = len(core_files)
	circom_o2_count = total // 2
	circom_o1_count = total // 4
	zokrates_count = total - circom_o2_count - circom_o1_count

	assignments: list[tuple[Path, BackendSpec]] = []
	for index, smt2_path in enumerate(core_files):
		if index < circom_o2_count:
			backend = BACKEND_SPECS[0]
		elif index < circom_o2_count + circom_o1_count:
			backend = BACKEND_SPECS[1]
		else:
			backend = BACKEND_SPECS[2]
		assignments.append((smt2_path, backend))
	return assignments


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Generate finite-field benchmarks from benchmarks/core into "
			"benchmarks/finite-field with a 50%% circom O2, 25%% circom O1, "
			"25%% zokrates split."
		)
	)
	parser.add_argument("--core-dir", type=Path, default=DEFAULT_CORE_DIR, help="Input core benchmark directory.")
	parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output finite-field benchmark directory.")
	parser.add_argument("--circom-compiler", default=None, help="Override circom compiler binary.")
	parser.add_argument("--zokrates-compiler", default=None, help="Override zokrates compiler binary.")
	parser.add_argument("--max-vars", type=int, default=None, help="Skip outputs whose compiled R1CS exceeds this variable count.")
	parser.add_argument("--skip-existing", action="store_true", help="Skip outputs that already exist.")
	parser.add_argument("--continue-on-error", action="store_true", help="Continue if one benchmark fails to convert.")
	parser.add_argument("--with-logs", action="store_true", help="Print per-file progress.")
	parser.add_argument("--keep-intermediate", type=Path, default=None, help="Directory for intermediate DSL files.")
	return parser.parse_args()


def resolve_compiler(backend: BackendSpec, args: argparse.Namespace) -> str | None:
	if backend.dsl == "circom":
		return args.circom_compiler
	if backend.dsl == "zokrates":
		return args.zokrates_compiler
	return backend.compiler


def main() -> int:
	args = parse_args()
	core_dir = args.core_dir.resolve()
	out_dir = args.out_dir.resolve()

	if not core_dir.exists():
		print(f"Core benchmark directory not found: {core_dir}", file=sys.stderr)
		return 1

	core_files = collect_core_files(core_dir)
	if not core_files:
		print(f"No .smt2 files found under {core_dir}", file=sys.stderr)
		return 1

	assignments = assign_backends(core_files)
	counts = {
		BACKEND_SPECS[0].label: sum(1 for _, backend in assignments if backend == BACKEND_SPECS[0]),
		BACKEND_SPECS[1].label: sum(1 for _, backend in assignments if backend == BACKEND_SPECS[1]),
		BACKEND_SPECS[2].label: sum(1 for _, backend in assignments if backend == BACKEND_SPECS[2]),
	}

	print(
		f"Generating {len(assignments)} finite-field benchmarks into {out_dir} "
		f"(circom_O2={counts['circom_O2']}, circom_O1={counts['circom_O1']}, "
		f"zokrates={counts['zokrates']})"
	)

	converted = 0
	for smt2_path, backend in assignments:
		relative_path = smt2_path.relative_to(core_dir)
		out_file = out_dir / relative_path
		try:
			if convert_bool_smt_to_ff(
				smt2_path=smt2_path,
				out_file=out_file,
				dsl=backend.dsl,
				compiler=resolve_compiler(backend, args),
				opt_level=backend.opt_level,
				max_vars=args.max_vars,
				skip_existing=args.skip_existing,
				with_logs=args.with_logs,
				keep_intermediate=args.keep_intermediate,
			):
				converted += 1
		except Exception as exc:
			if args.continue_on_error:
				print(f"Skipping {relative_path}: {exc}", file=sys.stderr)
				continue
			raise

	print(f"Converted {converted} file(s) into {out_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
