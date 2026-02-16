# unique_sat_5vars

Generated benchmark of uniquely satisfiable Boolean SMT-LIB2 formulas.

- Files: 1000 (`unique5_0001.smt2` ... `unique5_1000.smt2`)
- Variables per formula: 5 Boolean variables (`x1`..`x5`)
- Generator command:

```bash
python3 cli.py generate-unique-sat-benchmark \
  benchmarks/SMT-benchmarks/core/unique_sat_5vars \
  --count 1000 --nvars 5 --seed 42
```

Generator implementation:
- `src/cli/helper.py` (`generate-unique-sat-benchmark` command)
- `benchmarks/SMT-benchmarks/core/generate_unique_sat_benchmark.py` (standalone script)
