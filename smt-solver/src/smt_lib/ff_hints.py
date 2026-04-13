from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.smt_lib.smt_lib_parser import parse_smtlib2_ff
from src.smt_lib.zk_ir import (
	Assertion,
	BinaryExpression,
	UnaryExpression,
	Integer,
	Variable,
	Operator,
	VariableType,
)


_CVC5_HINT_WORKER = """\
import cvc5.pythonic  # must be first — before pysmt or any Cython extension
import pickle, sys
sys.path.insert(0, sys.argv[1])  # repo smt-solver dir
from src.smt_lib.ff_hints import _solve_ff_models
max_models = int(sys.argv[2]) if len(sys.argv) > 2 else 1
solving_timeout = int(sys.argv[3]) if len(sys.argv) > 3 else None
smtlib2 = sys.stdin.read()
models = _solve_ff_models(smtlib2, max_models=max_models, solving_timeout=solving_timeout)
sys.stdout.buffer.write(pickle.dumps(models))
"""


def _safe_int(x: Any) -> int:
	if hasattr(x, "as_long"):
		return int(x.as_long())
	if hasattr(x, "as_signed_long"):
		return int(x.as_signed_long())
	if hasattr(x, "getIntegerValue"):
		return int(x.getIntegerValue())
	try:
		return int(x)
	except Exception:
		raise TypeError(f"Cannot convert model value to int: {x!r} (type={type(x)})")


def _solve_ff_models(smtlib2: str, *, max_models: int = 1, solving_timeout: int | None = None) -> list[dict[str, int]]:
	"""In-process QF_FF model extraction using cvc5. Intended for subprocess use only."""
	import cvc5.pythonic as cv

	if max_models <= 0:
		return []

	circuit = parse_smtlib2_ff(smtlib2)
	p = _extract_prime(smtlib2)
	if p is None:
		raise ValueError("Missing finite field prime in QF_FF input.")
	F = cv.FiniteFieldSort(p)
	solver = cv.SolverFor("QF_FF")
	if solving_timeout is not None:
		solver.set("tlimit", solving_timeout * 1000)

	def ff_val(n: int):
		return cv.FiniteFieldVal(int(n) % p, F)

	var_map: dict[str, Any] = {}
	for var in list(circuit.inputs) + list(circuit.outputs):
		if var.variable_type != VariableType.FIELD:
			continue
		if var.name in var_map:
			continue
		v = cv.FiniteFieldElem(var.name, F)
		var_map[var.name] = v

	def expr_to_cv(expr):
		if isinstance(expr, Integer):
			return ff_val(expr.value)
		if isinstance(expr, Variable):
			return var_map[expr.name]
		if isinstance(expr, UnaryExpression):
			if expr.op != Operator.SUB:
				raise ValueError(f"Unsupported unary op in QF_FF hints: {expr.op}")
			return -expr_to_cv(expr.value)
		if isinstance(expr, BinaryExpression):
			if expr.op == Operator.ADD:
				return expr_to_cv(expr.lhs) + expr_to_cv(expr.rhs)
			if expr.op == Operator.MUL:
				return expr_to_cv(expr.lhs) * expr_to_cv(expr.rhs)
			if expr.op == Operator.EQU:
				return expr_to_cv(expr.lhs) == expr_to_cv(expr.rhs)
			raise ValueError(f"Unsupported binary op in QF_FF hints: {expr.op}")
		raise ValueError(f"Unsupported expression type in QF_FF hints: {type(expr)}")

	for stmt in circuit.statements:
		if not isinstance(stmt, Assertion):
			continue
		cond = expr_to_cv(stmt.value)
		solver.add(cond)

	models: list[dict[str, int]] = []
	for _ in range(max_models):
		res = solver.check()
		if res != cv.sat:
			break
		m = solver.model()
		model: dict[str, int] = {}
		for name, v in var_map.items():
			val = m.eval(v)
			model[name] = _safe_int(val)
		models.append(model)

		# block current model to get more
		block = []
		for name, v in var_map.items():
			block.append(v == ff_val(model[name]))
		if not block:
			break
		if len(block) == 1:
			solver.add(cv.Not(block[0]))
		else:
			solver.add(cv.Not(cv.And(block)))

	return models


def _extract_prime(smtlib2: str) -> int | None:
	# simple regex-free extraction: look for "FiniteField <p>"
	for line in smtlib2.splitlines():
		if "FiniteField" in line:
			parts = line.replace("(", " ").replace(")", " ").split()
			for i, part in enumerate(parts):
				if part == "FiniteField" and i + 1 < len(parts):
					if parts[i + 1].isdigit():
						return int(parts[i + 1])
	return None


def run_ff_hint_models_subprocess(
	smtlib2: str,
	*,
	max_models: int = 1,
	solving_timeout: int | None = None,
) -> list[dict[str, int]]:
	"""Run cvc5 in a subprocess to extract QF_FF models."""
	smt_solver_dir = str(Path(__file__).resolve().parents[2])
	cmd = [sys.executable, "-c", _CVC5_HINT_WORKER, smt_solver_dir, str(max_models)]
	if solving_timeout is not None:
		cmd.append(str(solving_timeout))
	proc = subprocess.run(
		cmd,
		input=smtlib2.encode("utf-8"),
		text=False,
		capture_output=True,
		timeout=solving_timeout + 10 if solving_timeout is not None else None,
	)
	if proc.returncode != 0:
		stderr = proc.stderr.decode("utf-8", errors="replace")
		raise RuntimeError(f"cvc5 hint subprocess failed:\n{stderr}")
	return pickle.loads(proc.stdout)
