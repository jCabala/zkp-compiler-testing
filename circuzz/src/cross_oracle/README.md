# cross_oracle

Shared home for cross-repo oracle/generator code:

- `config/`: oracle/generator shared config types
- `generation/`: SMT-fusion generation runner and persistent queue
- `adapters/`: generation backends (`native_smt_solver`)
- `oracle/`: SMT pipeline replay executors per DSL (`circom`, `gnark`, `noir`)

`circuzz` backends keep orchestration and delegate SMT pipeline execution to this package.
`cross_oracle` no longer requires the `fuse-smt-to-dsl` CLI command.
