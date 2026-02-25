# Artificial Bugs Toolchains

Expected checkout locations for compiler versions used in artificial-bug experiments.

## Circom compiler

Clone here:

```bash
git clone https://github.com/iden3/circom.git smt-solver/third_party/artificial-bugs/circom
```

Build binary expected by the experiment:

```bash
cd smt-solver/third_party/artificial-bugs/circom
cargo build --release
```

The `circom-artificial-bugs` experiment uses:

- `smt-solver/third_party/artificial-bugs/circom/target/release/circom`
