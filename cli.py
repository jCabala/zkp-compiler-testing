#!/usr/bin/env python3

from pathlib import Path
import click
from src.cli.helper import export_r1cs_command, generate_proof_command
from src.cli.solver import solve_circom_command

@click.group()
def cli():
    """SMT Solver CLI for Circom circuits."""
    pass

# --------------------------- Solving ----------------------------------

cli.add_command(solve_circom_command)

# --------------------------- Helper commands ----------------------------------

cli.add_command(export_r1cs_command)


cli.add_command(generate_proof_command)

# ------------------------------------- Main -----------------------------------------

if __name__ == "__main__":
    cli()
