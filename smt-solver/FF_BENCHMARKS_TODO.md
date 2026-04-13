# FF Benchmarks TODO

## Parsing & IR
- [x] Add QF_FF parser: support `set-logic QF_FF`, `define-sort`, `declare-fun`, `assert (= ...)`, `ff.add`, `ff.mul`, `ff.neg`, and `(as ffK F)` constants.
- [x] Add auto-detect `parse_smtlib2(...)` and route existing pipelines through it.
- [ ] Add sum-fusion for field variables (`_fused` names → `x1 + x2`) once basic FF parsing is stable.
- [ ] Add tests for sum-fusion semantics and output IR.

## CLI / Pipeline
- [ ] Add FF benchmarks to `tests/cli/solver_cli/test_solve_integration.py` **after FF hints are supported** so tests can run unchanged.
- [ ] Add a small FF test corpus under `tests/cli/solver_cli/data/ff/` (sat + unsat + picus cases).

## Hints (Important)
- [ ] Hints currently rely on Z3 models from the original SMT-LIB input and **do not work for QF_FF**.
- [ ] If we want FF hints, implement a cvc5-based model extractor for QF_FF and wire it into the hint pipeline.
## Benchmarks & Conversion
- [x] Add `bool-smt-to-ff` benchmark generation command.
- [x] Disable R1CS optimizations for benchmark generation (keep raw constraints).
- [ ] Add documentation for FF workflows (generation + solving flags).
