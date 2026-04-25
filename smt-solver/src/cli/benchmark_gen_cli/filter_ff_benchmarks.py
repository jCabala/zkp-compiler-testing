import json
import re
import shutil
from pathlib import Path

from src.smt_lib.ff_hints import run_ff_hint_models_subprocess, _extract_prime


def _declared_vars(smt2: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(r'\(\s*declare-(?:const|fun)\s+(\S+)', smt2):
        names.add(m.group(1))
    return names


def _assertions_use_variables(smt2: str, var_names: set[str]) -> bool:
    """Return True if any assert body references at least one declared variable."""
    for m in re.finditer(r'\(\s*assert\s+(.*?)\)\s*(?=\(|$)', smt2, re.DOTALL):
        body = m.group(1)
        for name in var_names:
            if re.search(rf'\b{re.escape(name)}\b', body):
                return True
    return False


def _inject_distinct_constraints(smt2: str, model: dict[str, int], p: int) -> str:
    asserts = [
        f"(assert (distinct {name} (ff #x{value:x} {p})))"
        for name, value in model.items()
    ]
    inject = "\n".join(asserts)
    return smt2.replace("(check-sat)", inject + "\n(check-sat)", 1)


def filter_ff_benchmarks(
    in_dir: Path,
    out_dir: Path,
    timeout: int,
    max_iterations: int = 5,
    stats_file: Path | None = None,
    log=print,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(in_dir.glob("*.smt2"))
    if not files:
        log(f"No .smt2 files found in {in_dir}")
        return

    stats = {
        "total": 0,
        "unsat": 0,
        "no_vars": 0,
        "unique": 0,
        "augmented": 0,
        "still_non_unique": 0,
        "too_few_vars": 0,
        "no_prime": 0,
    }
    REPORT_INTERVAL = 100

    def _report():
        accepted = stats["unique"] + stats["augmented"]
        log(
            f"  --- [{stats['total']}/{len(files)}] "
            f"accepted={accepted} | "
            f"unique={stats['unique']} augmented={stats['augmented']} | "
            f"rejected: unsat={stats['unsat']} no_vars={stats['no_vars']} "
            f"non_unique={stats['still_non_unique']} too_few_vars={stats['too_few_vars']} "
            f"no_prime={stats['no_prime']} ---"
        )
        if stats_file is not None:
            stats_file.write_text(json.dumps({**stats, "total_files": len(files)}, indent=2))

    for f in files:
        stats["total"] += 1
        smt2 = f.read_text()

        var_names = _declared_vars(smt2)
        if not _assertions_use_variables(smt2, var_names):
            log(f"  [discard]  {f.name} — assertions contain no variables, only constants")
            stats["no_vars"] += 1
        else:
            models = run_ff_hint_models_subprocess(smt2, max_models=2, solving_timeout=timeout)

            if len(models) == 0:
                log(f"  [unsat]    {f.name}")
                stats["unsat"] += 1

            elif len(models) == 1:
                shutil.copy(f, out_dir / f.name)
                log(f"  [unique]   {f.name}")
                stats["unique"] += 1

            else:
                # Non-unique: exclude the second discovered model with per-variable
                # finite-field disequality assertions, repeating for a bounded
                # number of rounds until uniqueness is reached or we give up.
                p = _extract_prime(smt2)
                if p is None:
                    log(f"  [skip]     {f.name} — could not extract prime")
                    stats["no_prime"] += 1
                else:
                    augmented_smt2 = smt2
                    current_models = models
                    unique_after_augmentation = False

                    for iteration in range(1, max_iterations + 1):
                        second_model = current_models[1]

                        if not second_model:
                            log(f"  [discard]  {f.name} — second model has no field variables")
                            stats["too_few_vars"] += 1
                            break

                        augmented_smt2 = _inject_distinct_constraints(augmented_smt2, second_model, p)
                        current_models = run_ff_hint_models_subprocess(
                            augmented_smt2,
                            max_models=2,
                            solving_timeout=timeout,
                        )

                        if len(current_models) == 1:
                            (out_dir / f.name).write_text(augmented_smt2)
                            log(f"  [augmented] {f.name} — unique after {iteration} iteration(s)")
                            stats["augmented"] += 1
                            unique_after_augmentation = True
                            break

                        if len(current_models) == 0:
                            log(f"  [discard]  {f.name} — became unsat after {iteration} iteration(s)")
                            stats["unsat"] += 1
                            break

                    if not unique_after_augmentation and len(current_models) >= 2:
                        log(
                            f"  [discard]  {f.name} — still non-unique after "
                            f"{max_iterations} iteration(s)"
                        )
                        stats["still_non_unique"] += 1

        if stats["total"] % REPORT_INTERVAL == 0:
            _report()

    _report()
