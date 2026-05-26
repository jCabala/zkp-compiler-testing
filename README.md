# FYP — Fuzzing ZKP Compilers

This repository contains the full codebase for an FYP at Imperial College London on fuzzing of zero-knowledge proof (ZKP) compilers.

## Repository layout

| Folder | Description |
|---|---|
| [`circuzz/`](circuzz/README.md) | Fork of the Circuzz metamorphic testing framework, extended with new backends, oracles, and generators. |
| [`smt-solver/`](smt-solver/README.md) | SMT-based oracle and CLI for compiling ZK DSL programs to SMT2, solving them, and driving YinYang fusion experiments. |
| [`evaluation/`](evaluation/) | Evaluation data, analysis notebooks, and results used in the final report (coverage, benchmark comparisons, bug reports). |
| [`vm_setup/`](vm_setup/README.md) | Scripts for provisioning the DoC VM environment (Podman installation, etc.). |
| [`report/`](report/README.md) | Final FYP report. |
