#!/usr/bin/env python3

import os
from pathlib import Path
import click
from src.cli.helper import export_r1cs_command, generate_proof_command, cnf_to_smtlib2_command, translate_to_circom_command, translate_to_gnark_command
from src.cli.solver import solve, solve_circom_command

@click.group()
def cli():
    """SMT Solver CLI for Circom circuits."""
    pass

# --------------------------- Solving ----------------------------------

cli.add_command(solve_circom_command)
cli.add_command(solve)

# --------------------------- Helper commands ----------------------------------

cli.add_command(export_r1cs_command)
cli.add_command(generate_proof_command)
cli.add_command(cnf_to_smtlib2_command)
cli.add_command(translate_to_circom_command)
cli.add_command(translate_to_gnark_command)

# ------------------------------------- Main -----------------------------------------

if __name__ == "__main__":
    cli()
