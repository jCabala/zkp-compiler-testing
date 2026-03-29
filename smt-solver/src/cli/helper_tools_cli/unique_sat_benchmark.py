import random
from pathlib import Path
from src.smt_lib import cnf_string_to_smt2


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


def generate_unique_sat_benchmarks(out_folder: Path, count: int = 1000, nvars: int = 5, seed: int = 42, log=print):
	"""Generate a benchmark of uniquely satisfiable SMT-LIB2 formulas."""
	if count <= 0:
		raise ValueError("count must be > 0")
	if nvars <= 0:
		raise ValueError("nvars must be > 0")

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

	log(f"Generated {generated} unique SAT SMT-LIB2 file(s) in {out_folder}")
