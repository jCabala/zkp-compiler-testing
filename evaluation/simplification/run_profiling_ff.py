#!/usr/bin/env python3
"""
Run profiling-instrumented Circom on finite-field SMT2 benchmarks and print summaries.

This wraps run_profiling.py over a set of benchmark directories and saves
per-folder JSON results.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SMT_SOLVER_DIR = REPO_ROOT / "smt-solver"
RUN_PROFILING = SCRIPT_DIR / "run_profiling.py"


def _run(cmd: list[str]) -> None:
	subprocess.run(cmd, check=True)


def main() -> int:
	parser = argparse.ArgumentParser(description="Profile Circom on FF benchmarks")
	parser.add_argument(
		"--benchmarks-root",
		type=Path,
		default=SMT_SOLVER_DIR / "benchmarks" / "SMT-benchmarks" / "finite-field" / "bool-based",
		help="Root directory containing FF benchmark folders",
	)
	parser.add_argument(
		"--pattern",
		type=str,
		default="unique_sat_1to5vars_circom_O*",
		help="Glob pattern for benchmark folders under benchmarks-root",
	)
	parser.add_argument("--max-files", type=int, default=10, help="Max files per folder")
	parser.add_argument("--timeout", type=int, default=60, help="Timeout per compilation")
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=SCRIPT_DIR / "results-ff",
		help="Directory to store JSON results",
	)
	args = parser.parse_args()

	bench_root = args.benchmarks_root
	folders = sorted(bench_root.glob(args.pattern))
	if not folders:
		print(f"No benchmark folders found under {bench_root} matching {args.pattern}")
		return 1

	args.output_dir.mkdir(parents=True, exist_ok=True)

	for folder in folders:
		out_file = args.output_dir / f"{folder.name}.json"
		print(f"\n=== Profiling {folder} ===")
		cmd = [
			sys.executable,
			str(RUN_PROFILING),
			"--benchmarks-dir",
			str(folder),
			"--max-files",
			str(args.max_files),
			"--timeout",
			str(args.timeout),
			"--output",
			str(out_file),
		]
		_run(cmd)

	print(f"\nDone. Results saved to {args.output_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
