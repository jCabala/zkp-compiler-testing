#!/usr/bin/env python3
"""
Analyse R1CS constraint structure for benchmark sets.

Accepts either:
  - A directory of .r1cs.json files (pre-compiled)
  - A directory of .smt2 files        (auto-translated → Circom → R1CS)
  - A directory of vars-NN subdirs    (per-variable-count breakdown)

A constraint [A, B, C] is:
  - LINEAR   if A or B contains only the constant term (key "0")
  - QUADRATIC otherwise (both sides have variable terms)

Usage:
  python3 analyse-r1cs.py                          # default bool/ff dirs
  python3 analyse-r1cs.py <dir> [<dir> ...]        # explicit dirs (labelled by name)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean, median, stdev

SCRIPT_DIR = Path(__file__).resolve().parent
SMT_ROOT   = (SCRIPT_DIR / "../../smt-solver").resolve()

DEFAULT_R1CS_DIRS = {
    "bool": SCRIPT_DIR / "r1cs" / "bool",
    "ff":   SCRIPT_DIR / "r1cs" / "ff",
}


# ── R1CS helpers ─────────────────────────────────────────────────────────────

def is_linear(constraint: list[dict]) -> bool:
    a, b, _ = constraint
    return not (any(k != "0" for k in a) and any(k != "0" for k in b))


def analyse_r1cs_file(path: Path) -> dict:
    data = json.loads(path.read_text())
    constraints = data.get("constraints", [])
    n = len(constraints)
    linear    = sum(1 for c in constraints if is_linear(c))
    quadratic = n - linear
    return {
        "n_constraints": n,
        "n_vars":        data.get("nVars", 0),
        "linear":        linear,
        "quadratic":     quadratic,
        "pct_quadratic": 100 * quadratic / n if n else 0.0,
    }


# ── Compilation pipeline ──────────────────────────────────────────────────────

def smt2_to_r1cs(smt_file: Path, tmp_dir: Path) -> Path | None:
    """Translate one .smt2 file to R1CS JSON via Circom. Returns path or None."""
    circom_file = tmp_dir / (smt_file.stem + ".circom")
    r1cs_file   = tmp_dir / (smt_file.stem + ".r1cs.json")

    # smt2 → circom
    r = subprocess.run(
        [sys.executable, str(SMT_ROOT / "cli.py"), "smt-to-dsl",
         "--dsl", "circom", str(smt_file.parent), str(tmp_dir),
         "--max-out", "1"],
        capture_output=True, cwd=SMT_ROOT,
    )
    if not circom_file.exists():
        return None

    # circom → r1cs json
    r = subprocess.run(
        [sys.executable, str(SMT_ROOT / "cli.py"), "export-r1cs-command",
         str(circom_file), "-o", str(r1cs_file)],
        capture_output=True, cwd=SMT_ROOT,
    )
    return r1cs_file if r1cs_file.exists() else None


def collect_r1cs_from_dir(src_dir: Path) -> list[dict]:
    """Return list of analyse_r1cs_file dicts from a directory.
    Handles .r1cs.json directly, or .smt2 via auto-compilation."""
    json_files = sorted(src_dir.glob("*.r1cs.json"))
    if json_files:
        return [analyse_r1cs_file(f) for f in json_files]

    smt_files = sorted(src_dir.glob("*.smt2"))
    if not smt_files:
        return []

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for sf in smt_files:
            # copy just this file into a temp staging dir so smt-to-dsl only sees one file
            stage = tmp_dir / sf.stem
            stage.mkdir()
            import shutil; shutil.copy(sf, stage / sf.name)
            r1cs = None
            circom_out = tmp_dir / (sf.stem + ".circom")
            r = subprocess.run(
                [sys.executable, str(SMT_ROOT / "cli.py"), "smt-to-dsl",
                 "--dsl", "circom", str(stage), str(tmp_dir)],
                capture_output=True, cwd=SMT_ROOT,
            )
            if circom_out.exists():
                r1cs_out = tmp_dir / (sf.stem + ".r1cs.json")
                subprocess.run(
                    [sys.executable, str(SMT_ROOT / "cli.py"), "export-r1cs-command",
                     str(circom_out), "-o", str(r1cs_out)],
                    capture_output=True, cwd=SMT_ROOT,
                )
                if r1cs_out.exists():
                    results.append(analyse_r1cs_file(r1cs_out))
    return results


# ── Summary helpers ───────────────────────────────────────────────────────────

def summarise(stats: list[dict]) -> dict:
    if not stats:
        return {}
    def avg(key): return mean(s[key] for s in stats)
    def med(key): return median(s[key] for s in stats)
    def sd(key):  return stdev(s[key] for s in stats) if len(stats) > 1 else 0.0
    return {
        "n":                  len(stats),
        "constraints_mean":   avg("n_constraints"),
        "constraints_median": med("n_constraints"),
        "constraints_stdev":  sd("n_constraints"),
        "vars_mean":          avg("n_vars"),
        "linear_mean":        avg("linear"),
        "quadratic_mean":     avg("quadratic"),
        "pct_quadratic_mean": avg("pct_quadratic"),
    }


def print_summary(label: str, s: dict) -> None:
    print(f"  {label} ({s['n']} benchmarks)")
    print(f"    Constraints  mean={s['constraints_mean']:.1f}  "
          f"median={s['constraints_median']:.1f}  stdev={s['constraints_stdev']:.1f}")
    print(f"    Variables    mean={s['vars_mean']:.1f}")
    print(f"    Linear       mean={s['linear_mean']:.1f}")
    print(f"    Quadratic    mean={s['quadratic_mean']:.1f}  "
          f"({s['pct_quadratic_mean']:.1f}%)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dirs", nargs="*", type=Path,
                        help="Directories to analyse (default: bool/ff r1cs dirs)")
    args = parser.parse_args()

    if args.dirs:
        # Check if any dir contains vars-NN subdirs (benchmark-size layout)
        for top_dir in args.dirs:
            var_dirs = sorted(top_dir.glob("vars-??"))
            if var_dirs:
                print(f"Per-variable-count analysis: {top_dir.name}")
                print("=" * 60)
                hdr = f"  {'Vars':>6}  {'N':>4}  {'Mean constraints':>18}  {'Mean vars':>10}  {'Quadratic%':>11}"
                print(hdr)
                print("  " + "-" * (len(hdr) - 2))
                for vd in var_dirs:
                    var_count = int(vd.name.split("-")[1])
                    stats = collect_r1cs_from_dir(vd)
                    if not stats:
                        continue
                    s = summarise(stats)
                    print(f"  {var_count:>6}  {s['n']:>4}  "
                          f"{s['constraints_mean']:>18.1f}  "
                          f"{s['vars_mean']:>10.1f}  "
                          f"{s['pct_quadratic_mean']:>10.1f}%")
                print()
            else:
                label = top_dir.name
                stats = collect_r1cs_from_dir(top_dir)
                if not stats:
                    print(f"[warn] no data in {top_dir}")
                    continue
                print("R1CS Constraint Analysis")
                print("=" * 50)
                print_summary(label, summarise(stats))
                print()
    else:
        # Default: bool vs ff
        all_stats: dict[str, list[dict]] = {}
        for label, r1cs_dir in DEFAULT_R1CS_DIRS.items():
            if not r1cs_dir.exists():
                print(f"[warn] {r1cs_dir} does not exist — run compile.sh first")
                continue
            files = sorted(r1cs_dir.glob("*.r1cs.json"))
            if not files:
                print(f"[warn] no .r1cs.json files in {r1cs_dir}")
                continue
            all_stats[label] = [analyse_r1cs_file(f) for f in files]

        if not all_stats:
            print("No R1CS data found.")
            return

        print("R1CS Constraint Analysis")
        print("=" * 50)
        for label, stats in all_stats.items():
            print_summary(label, summarise(stats))
            print()

        if set(all_stats) == {"bool", "ff"}:
            bool_files = {f.stem: f for f in (SCRIPT_DIR / "r1cs" / "bool").glob("*.r1cs.json")}
            ff_files   = {f.stem: f for f in (SCRIPT_DIR / "r1cs" / "ff").glob("*.r1cs.json")}
            common = sorted(bool_files.keys() & ff_files.keys())
            if common:
                print(f"Paired comparison ({len(common)} matched benchmarks)")
                print("-" * 50)
                constraint_ratios = [
                    analyse_r1cs_file(ff_files[s])["n_constraints"] /
                    analyse_r1cs_file(bool_files[s])["n_constraints"]
                    for s in common
                    if analyse_r1cs_file(bool_files[s])["n_constraints"] > 0
                ]
                if constraint_ratios:
                    print(f"  FF/Bool constraint ratio  "
                          f"mean={mean(constraint_ratios):.2f}  "
                          f"median={median(constraint_ratios):.2f}")


if __name__ == "__main__":
    main()
