from pathlib import Path
from src.smt_lib import cnf_string_to_smt2


def _sudoku_var_id(row: int, col: int, digit: int) -> int:
	"""Map (row, col, digit) in 1..9 to DIMACS variable id in 1..729."""
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
			clauses.append([_sudoku_var_id(r, c, d) for d in range(1, 10)])
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


def sudoku17_to_smtlib2(sudoku_file: Path, out_folder: Path, start: int = 1, max_out: int | None = None, log=print):
	"""Convert Royle sudoku17 text file into SMT-LIB2 files via CNF->SMT utility."""
	if start <= 0:
		raise ValueError("start must be >= 1")
	if max_out is not None and max_out <= 0:
		raise ValueError("max_out must be > 0 when provided")

	out_folder.mkdir(parents=True, exist_ok=True)

	lines = [ln.strip() for ln in sudoku_file.read_text().splitlines() if ln.strip()]
	total = len(lines)
	begin = start - 1
	if begin >= total:
		log(f"No puzzles to convert: start={start}, total={total}")
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

	log(f"Converted {converted} puzzle(s) from {sudoku_file} to SMT-LIB2 in {out_folder}")
