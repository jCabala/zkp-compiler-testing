# Coverage Evaluation

Measures code coverage of the Circom compiler when exercised by each fuzzing/testing tool.
Coverage is collected using LLVM instrumentation (`llvm-cov`) inside Podman containers.

## Prerequisites

Build the coverage-instrumented Podman images (one-time setup):

```bash
./build_podman.sh
```

## Running Coverage

Each experiment has its own `coverage.sh` that collects `.profraw` files and then
calls `generate_report.sh` automatically on exit.

```bash
# Circuzz (arithmetic | fully-constraint | all)
./circuzz/coverage.sh arithmetic
./circuzz/coverage.sh fully-constraint
./circuzz/coverage.sh all          # runs both in parallel

# SMT-solver fuzzer (sat, picus, or both)
./smt-solver/coverage.sh

# Circom test suite
./test-suite/coverage.sh
```

Reports are written to `obj/<experiment>/coverage_report/`:
- `html/index.html` — browsable line-level coverage
- `circom_coverage.lcov` — LCOV data for further tooling
- `summary.txt` — per-file coverage summary

You can override the experiment duration (default 60 s) with `DURATION=<seconds>`.

## Serving Reports

```bash
./serve_report.sh smt-solver          # serve a single experiment report
./serve_report.sh test-suite
./serve_report.sh diff                # auto-detect all available reports
./serve_report.sh diff circuzz-arithmetic circuzz-fully-constraint
```

Then open `http://127.0.0.1:8000` in a browser.

## Differential Reports

Generate a side-by-side diff between two or more experiments:

```bash
./generate_diff_report.py circuzz-arithmetic smt-solver
./serve_report.sh diff circuzz-arithmetic smt-solver
```
