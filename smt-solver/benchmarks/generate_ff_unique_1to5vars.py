#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT_DIR / "benchmarks" / "SMT-benchmarks" / "core" / "unique_sat_1to5vars"
SUBSET_DIR = ROOT_DIR / "benchmarks" / "SMT-benchmarks" / "core" / "unique_sat_1to5vars_subset10"
OUT_BASE = ROOT_DIR / "benchmarks" / "SMT-benchmarks" / "finite-field"


def _pick_two_per_nvars() -> list[Path]:
	selected: list[Path] = []
	for n in range(1, 6):
		files = sorted(CORE_DIR.glob(f"unique{n}_*.smt2"))
		if len(files) < 2:
			raise RuntimeError(f"Expected at least 2 files for unique{n}_*.smt2")
		selected.extend(files[:2])
	return selected


def _run(cmd: list[str]) -> None:
	subprocess.run(cmd, check=True)


def main() -> int:
	print(f"Selecting 2 files per var-count (1..5) into: {SUBSET_DIR}")
	if SUBSET_DIR.exists():
		for f in SUBSET_DIR.glob("*.smt2"):
			f.unlink()
	else:
		SUBSET_DIR.mkdir(parents=True, exist_ok=True)

	selected = _pick_two_per_nvars()
	for f in selected:
		target = SUBSET_DIR / f.name
		target.write_text(f.read_text())

	print(f"Creating finite-field benchmarks from {SUBSET_DIR}")

	for opt in ("O0", "O1", "O2"):
		out_dir = OUT_BASE / f"unique_sat_1to5vars_circom_{opt}"
		print(f"Circom {opt} -> {out_dir}")
		_run([
			sys.executable,
			str(ROOT_DIR / "cli.py"),
			"bool-smt-to-ff",
			str(SUBSET_DIR),
			str(out_dir),
			"--dsl",
			"circom",
			"--opt-level",
			opt,
		])

	for opt in ("O0", "O1", "O2"):
		out_dir = OUT_BASE / f"unique_sat_1to5vars_gnark_{opt}"
		print(f"Gnark {opt} -> {out_dir}")
		_run([
			sys.executable,
			str(ROOT_DIR / "cli.py"),
			"bool-smt-to-ff",
			str(SUBSET_DIR),
			str(out_dir),
			"--dsl",
			"gnark",
			"--opt-level",
			opt,
			"--suffix",
			f"gnark_{opt}",
		])

	print("Done.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
