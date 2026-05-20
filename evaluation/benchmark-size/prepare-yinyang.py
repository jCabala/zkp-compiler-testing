#!/usr/bin/env python3
"""
Generate yinyang-mutated benchmarks from the padded benchmark set.

For each vars-NN directory in benchmarks/padded/, runs yinyang semantic
fusion to produce mutant SMT2 files of known-SAT satisfiability. Mutants
are saved to benchmarks/yinyang/vars-NN/.

A lightweight capture-solver is used: it copies each mutant yinyang sends
it into the output directory and replies "sat", so yinyang keeps generating.

Usage:
  python3 prepare-yinyang.py [--iterations N] [--seed N]
"""
from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
SMT_ROOT     = (SCRIPT_DIR / "../../smt-solver").resolve()
PADDED_DIR   = SCRIPT_DIR / "benchmarks" / "padded"
YINYANG_CLI    = SMT_ROOT / "third_party" / "yinyang" / "yinyang_cli.py"
FUSION_CONFIG  = SMT_ROOT / "experiments" / "legacy" / "sat_fusion" / "sat_fusion_config.txt"
PYENV_PYTHON = subprocess.run(
    ["pyenv", "which", "python3"], capture_output=True, text=True
).stdout.strip() or sys.executable

CAPTURE_SOLVER_TEMPLATE = """\
#!/usr/bin/env bash
# Capture-solver: save the mutant and reply sat.
cp "$1" "$YINYANG_CAPTURE_DIR/$(date +%s%N)-$(basename "$1")"
echo "sat"
"""


def make_capture_solver(tmp_dir: Path) -> Path:
    path = tmp_dir / "capture_solver.sh"
    path.write_text(CAPTURE_SOLVER_TEMPLATE)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


def run_yinyang(
    solver_script: Path,
    seed_dir: Path,
    capture_dir: Path,
    scratch_dir: Path,
    iterations: int,
    seed: int,
    log_dir: Path,
) -> int:
    env = os.environ.copy()
    env["YINYANG_CAPTURE_DIR"] = str(capture_dir)

    cmd = [
        PYENV_PYTHON,
        str(YINYANG_CLI),
        str(solver_script),
        "--oracle", "sat",
        "--config", str(FUSION_CONFIG),
        "--iterations", str(iterations),
        "--seed", str(seed),
        "--logfolder", str(log_dir),
        "--scratchfolder", str(scratch_dir),
        str(seed_dir),
    ]

    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate yinyang-mutated benchmarks")
    parser.add_argument("--iterations", type=int, default=5, help="Yinyang iterations per seed pair (default: 5)")
    parser.add_argument("--seed", type=int, default=42, help="Yinyang random seed (default: 42)")
    parser.add_argument("--max-per-var", type=int, default=5, help="Max mutants to keep per vars-NN dir (default: 5)")
    args = parser.parse_args()

    out_root = SCRIPT_DIR / "benchmarks" / "yinyang"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        solver_script = make_capture_solver(tmp_dir)

        var_dirs = sorted(PADDED_DIR.glob("vars-??"))
        for var_dir in var_dirs:
            var_count = int(var_dir.name.split("-")[1])
            if not any(var_dir.glob("*.smt2")):
                print(f"vars={var_count:2d}  (empty, skipping)")
                continue

            capture_dir = out_root / var_dir.name
            capture_dir.mkdir(parents=True, exist_ok=True)
            scratch_dir = tmp_dir / f"scratch-{var_dir.name}"
            scratch_dir.mkdir()
            log_dir = tmp_dir / f"logs-{var_dir.name}"
            log_dir.mkdir()

            before = len(list(capture_dir.glob("*.smt2")))
            print(f"vars={var_count:2d}  generating mutants ...", end="", flush=True)

            run_yinyang(solver_script, var_dir, capture_dir, scratch_dir, args.iterations, args.seed, log_dir)

            all_files = sorted(capture_dir.glob("*.smt2"))
            excess = all_files[args.max_per_var:]
            for f in excess:
                f.unlink()

            after = len(list(capture_dir.glob("*.smt2")))
            print(f"  {after - before} new mutants  (total: {after})")

    print(f"\nDone. Mutants written to {out_root}")


if __name__ == "__main__":
    main()
