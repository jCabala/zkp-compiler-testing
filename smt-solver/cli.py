#!/usr/bin/env python3

import os
from pathlib import Path
import click
from src.cli.helper_tools_cli.commands import export_r1cs_command, generate_proof_command, cnf_to_smtlib2_command, generate_unique_sat_benchmark_command, prune_smtlib2_folder_command, translate_to_dsl_command
from src.cli.benchmark_gen_cli.commands import bool_smt_to_ff_command, generate_ff_benchmark_suite_command, sudoku17_to_smtlib2_command, filter_ff_benchmarks_command, generate_poseidon_benchmarks_command
from src.cli.solver_cli.commands import solve

@click.group()
def cli():
    """SMT Solver CLI for Circom circuits."""
    pass

# --------------------------- Solving ----------------------------------

cli.add_command(solve)

# --------------------------- Helper commands ----------------------------------

cli.add_command(export_r1cs_command)
cli.add_command(generate_proof_command)
cli.add_command(cnf_to_smtlib2_command)
cli.add_command(generate_unique_sat_benchmark_command)
cli.add_command(prune_smtlib2_folder_command)
cli.add_command(translate_to_dsl_command)
cli.add_command(bool_smt_to_ff_command)
cli.add_command(generate_ff_benchmark_suite_command)
cli.add_command(sudoku17_to_smtlib2_command)
cli.add_command(filter_ff_benchmarks_command)
cli.add_command(generate_poseidon_benchmarks_command)

# ------------------------------------- Main -----------------------------------------

if __name__ == "__main__":
    cli()
