#!/usr/bin/env python3

"""
Generate a benchmark of uniquely satisfiable SMT-LIB2 formulas.

Default output:
- 1000 files
- 5 Boolean variables per file
- each file has exactly one satisfying assignment

Implementation note:
We generate a random CNF over n vars that keeps one target assignment and
eliminates all others, then use the existing `cnf_string_to_smt2` utility.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable

from src.smt_lib import cnf_string_to_smt2


def all_assignments(nvars: int) -> list[tuple[bool, ...]]:
    out: list[tuple[bool, ...]] = []
    for mask in range(1 << nvars):
        out.append(tuple(bool((mask >> i) & 1) for i in range(nvars)))
    return out


def lit_value(lit: int, assignment: tuple[bool, ...]) -> bool:
    idx = abs(lit) - 1
    val = assignment[idx]
    return val if lit > 0 else (not val)


def clause_satisfied(clause: tuple[int, ...], assignment: tuple[bool, ...]) -> bool:
    return any(lit_value(l, assignment) for l in clause)


def cnf_unique_model_count(clauses: Iterable[tuple[int, ...]], universe: list[tuple[bool, ...]]) -> int:
    return sum(1 for a in universe if all(clause_satisfied(c, a) for c in clauses))


def random_clause_that_keeps_target(
    rng: random.Random, nvars: int, target: tuple[bool, ...], width_min: int = 1, width_max: int = 3
) -> tuple[int, ...]:
    width = rng.randint(width_min, min(width_max, nvars))
    vars_chosen = rng.sample(range(1, nvars + 1), width)
    lits: list[int] = []
    for v in vars_chosen:
        sign = rng.choice([1, -1])
        lits.append(sign * v)

    # Ensure target satisfies the clause by flipping one literal if needed.
    if not clause_satisfied(tuple(lits), target):
        j = rng.randrange(len(lits))
        v = abs(lits[j])
        target_val = target[v - 1]
        lits[j] = v if target_val else -v
    return tuple(lits)


def build_unique_cnf(rng: random.Random, nvars: int) -> tuple[list[tuple[int, ...]], tuple[bool, ...]]:
    universe = all_assignments(nvars)
    target = rng.choice(universe)
    remaining = {a for a in universe if a != target}
    clauses: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()

    # Build clauses until only target remains.
    attempts = 0
    while remaining:
        attempts += 1
        if attempts > 20000:
            raise RuntimeError("Could not construct a unique CNF in allotted attempts.")

        c = random_clause_that_keeps_target(rng, nvars, target)
        if c in seen:
            continue

        killed = {a for a in remaining if not clause_satisfied(c, a)}
        if not killed:
            continue

        seen.add(c)
        clauses.append(c)
        remaining.difference_update(killed)

    # Add a few extra target-satisfying clauses for syntactic diversity.
    extra = rng.randint(0, 4)
    for _ in range(extra):
        c = random_clause_that_keeps_target(rng, nvars, target)
        if c not in seen:
            seen.add(c)
            clauses.append(c)

    # Safety check: exactly one model.
    models = cnf_unique_model_count(clauses, universe)
    if models != 1:
        raise RuntimeError(f"Generator bug: expected 1 model, got {models}")

    return clauses, target


def clauses_to_dimacs(nvars: int, clauses: list[tuple[int, ...]]) -> str:
    lines = [f"p cnf {nvars} {len(clauses)}"]
    for c in clauses:
        lines.append(" ".join(str(l) for l in c) + " 0")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate unique SAT SMT2 benchmark files.")
    parser.add_argument("--out-dir", type=Path, default=Path("benchmarks/SMT-benchmarks/core/unique_sat_5vars"))
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--nvars", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.count <= 0:
        raise ValueError("--count must be > 0")
    if args.nvars <= 0:
        raise ValueError("--nvars must be > 0")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    generated = 0

    while generated < args.count:
        clauses, target = build_unique_cnf(rng, args.nvars)

        dimacs = clauses_to_dimacs(args.nvars, clauses)
        smt2 = cnf_string_to_smt2(dimacs)
        smt2 = f"; unique_target={''.join('1' if b else '0' for b in target)}\n{smt2}"

        generated += 1
        out = args.out_dir / f"unique5_{generated:04d}.smt2"
        out.write_text(smt2)

    print(f"Generated {generated} unique SAT SMT2 files in {args.out_dir}")


if __name__ == "__main__":
    main()
