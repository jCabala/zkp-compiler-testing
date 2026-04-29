#!/usr/bin/env python3

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Create a custom benchmark folder by sampling .smt2 files from multiple "
			"input folders as uniformly as possible."
		)
	)
	parser.add_argument(
		"in_dirs",
		nargs="+",
		type=Path,
		help="Input benchmark folders to sample from.",
	)
	parser.add_argument(
		"--out-dir",
		required=True,
		type=Path,
		help="Output folder that will receive the sampled .smt2 files.",
	)
	parser.add_argument(
		"--num-values",
		required=True,
		type=int,
		help="Target number of sampled benchmark files to write.",
	)
	parser.add_argument(
		"--seed",
		type=int,
		default=0,
		help="Random seed used for reproducible sampling.",
	)
	return parser.parse_args()


def collect_files(folder: Path) -> list[Path]:
	return sorted(path for path in folder.rglob("*.smt2") if path.is_file())


def compute_targets(groups: list[list[Path]], total: int) -> list[int]:
	if total < 0:
		raise ValueError("--num-values must be non-negative")
	if not groups:
		return []

	targets = [total // len(groups)] * len(groups)
	for idx in range(total % len(groups)):
		targets[idx] += 1

	capacities = [len(group) for group in groups]
	assigned = [min(target, capacity) for target, capacity in zip(targets, capacities)]
	remaining = total - sum(assigned)

	while remaining > 0:
		progress = False
		for idx, capacity in enumerate(capacities):
			if assigned[idx] < capacity:
				assigned[idx] += 1
				remaining -= 1
				progress = True
				if remaining == 0:
					break
		if not progress:
			break

	return assigned


def unique_output_path(out_dir: Path, source: Path, used_names: set[str]) -> Path:
	name = source.name
	if name not in used_names:
		used_names.add(name)
		return out_dir / name

	prefix = source.parent.name or "bench"
	candidate = f"{prefix}__{name}"
	if candidate not in used_names:
		used_names.add(candidate)
		return out_dir / candidate

	counter = 1
	stem = source.stem
	suffix = source.suffix
	while True:
		candidate = f"{prefix}__{stem}__{counter}{suffix}"
		if candidate not in used_names:
			used_names.add(candidate)
			return out_dir / candidate
		counter += 1


def main() -> int:
	args = parse_args()
	in_dirs = [path.resolve() for path in args.in_dirs]
	out_dir = args.out_dir.resolve()

	for folder in in_dirs:
		if not folder.exists():
			print(f"Input folder not found: {folder}", file=sys.stderr)
			return 1
		if not folder.is_dir():
			print(f"Input path is not a directory: {folder}", file=sys.stderr)
			return 1

	groups = [collect_files(folder) for folder in in_dirs]
	for folder, files in zip(in_dirs, groups):
		if not files:
			print(f"No .smt2 files found under {folder}", file=sys.stderr)
			return 1

	total_available = sum(len(group) for group in groups)
	target_total = min(args.num_values, total_available)

	rng = random.Random(args.seed)
	for group in groups:
		rng.shuffle(group)

	targets = compute_targets(groups, target_total)
	out_dir.mkdir(parents=True, exist_ok=True)

	used_names: set[str] = set()
	written = 0
	for folder, files, target in zip(in_dirs, groups, targets):
		selected = files[:target]
		for source in selected:
			destination = unique_output_path(out_dir, source, used_names)
			shutil.copy2(source, destination)
			written += 1
		print(f"{folder}: selected {len(selected)} of {len(files)} file(s)")

	if target_total < args.num_values:
		print(
			f"Requested {args.num_values} file(s), but only {target_total} were available across all folders.",
			file=sys.stderr,
		)

	print(f"Wrote {written} sampled benchmark file(s) into {out_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
