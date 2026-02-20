from __future__ import annotations

import json
import random
import re
import shutil
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from types import SimpleNamespace

from cross_oracle.adapters.base import FusionGeneratorBackend
from cross_oracle.generation.types import SMTFusionProgram, SMTFusionRunConfig


def _extract_gnark_fragment_for_circuzz(go_source: str) -> str:
    start_idx = go_source.find("\ntype ")
    if start_idx == -1:
        start_idx = go_source.find("type ")
    if start_idx == -1:
        raise ValueError("Unable to locate Gnark type definition in generated source")

    end_idx = go_source.find("\nfunc main()")
    if end_idx == -1:
        raise ValueError("Unable to locate Gnark main() in generated source")

    fragment = go_source[start_idx:end_idx].strip()
    return fragment + "\n"


def _sanitize_noir_package_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not cleaned:
        cleaned = "noir_case"
    if cleaned[0].isdigit():
        cleaned = f"p_{cleaned}"
    return cleaned.lower()


def _write_noir_project(project_dir: Path, package_name: str, main_nr_source: str):
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.nr").write_text(main_nr_source)

    nargo_toml = project_dir / "Nargo.toml"
    nargo_toml.write_text(
        "\n".join(
            [
                "[package]",
                f'name = "{package_name}"',
                'type = "bin"',
                'authors = [""]',
                "",
                "[dependencies]",
                "",
            ]
        )
    )


@contextmanager
def _solver_import_paths(solver_root: Path):
    root_str = str(solver_root)
    src_str = str(solver_root / "src")
    yy_str = str(solver_root / "third_party" / "yinyang")

    added: list[str] = []
    for path in [root_str, src_str, yy_str]:
        if path not in sys.path:
            sys.path.insert(0, path)
            added.append(path)

    try:
        yield
    finally:
        for path in added:
            try:
                sys.path.remove(path)
            except ValueError:
                pass


class NativeSmtSolverBackend(FusionGeneratorBackend):
    """
    Generate fused programs using smt-solver internals directly,
    without going through smt-solver CLI commands.
    """

    def generate(
        self,
        working_dir: Path,
        config: SMTFusionRunConfig,
        seed: int | None = None,
    ) -> list[SMTFusionProgram]:
        solver_root = Path(config.smt_solver_path)
        if not solver_root.is_dir():
            raise ValueError(f"unable to locate smt-solver root at '{solver_root}'")

        in_dir = Path(config.smt_seed_dir)
        if not in_dir.is_absolute():
            in_dir = solver_root / in_dir
        if not in_dir.is_dir():
            raise ValueError(f"unable to locate SMT seed directory '{in_dir}'")

        out_dir = working_dir / "smt_fusion"
        out_smt_dir = out_dir / "smt2"
        out_dsl_dir = out_dir / "dsl"
        out_sol_dir = out_dir / "solutions"
        shutil.rmtree(out_dir, ignore_errors=True)
        out_smt_dir.mkdir(parents=True, exist_ok=True)
        out_dsl_dir.mkdir(parents=True, exist_ok=True)
        out_sol_dir.mkdir(parents=True, exist_ok=True)

        with _solver_import_paths(solver_root):
            from src.backends.circom.emitter import EmitVisitor as CircomEmitter
            from src.backends.circom.ir2circom import IR2CircomVisitorConstrainAssertions
            from src.backends.gnark.emitter import EmitVisitor as GnarkEmitter
            from src.backends.gnark.ir2gnark import IR2GnarkVisitor
            from src.backends.noir.emitter import EmitVisitor as NoirEmitter
            from src.backends.noir.ir2noir import IR2NoirVisitor
            from src.smt_lib.prune import run_smt_solver_models
            from src.smt_lib.smt_lib_parser import parse_smtlib2_core
            from src.smt_lib.zk_ir import Circuit
            from third_party.yinyang.yinyang.src.mutators.SemanticFusion.SemanticFusion import SemanticFusion
            from third_party.yinyang.yinyang.src.parsing.Parse import parse_file

            def translate_smtlib2_to_dsl(smtlib2: str, dsl: str) -> tuple[str, str]:
                circuit_ir: Circuit = parse_smtlib2_core(smtlib2)

                if dsl == "circom":
                    rng = Random(0)
                    ir2circom_visitor = IR2CircomVisitorConstrainAssertions(
                        constraint_assignment_probability=1,
                        rng=rng,
                    )
                    circom_ir = ir2circom_visitor.visit_circuit(circuit_ir)
                    emitter = CircomEmitter()
                    circom_source = emitter.emit(circom_ir)
                    circom_source = circom_source.replace("../circomlib/", "")
                    return circom_source, ".circom"

                if dsl == "gnark":
                    ir2gnark_visitor = IR2GnarkVisitor(circuzz_compat=True)
                    gnark_ir = ir2gnark_visitor.visit_circuit(circuit_ir)
                    emitter = GnarkEmitter()
                    gnark_source = emitter.emit(gnark_ir)
                    return _extract_gnark_fragment_for_circuzz(gnark_source), ".go"

                if dsl == "noir":
                    ir2noir_visitor = IR2NoirVisitor()
                    noir_ast = ir2noir_visitor.visit_circuit(circuit_ir)
                    emitter = NoirEmitter()
                    return emitter.emit(noir_ast), ".nr"

                raise ValueError(f"Unsupported DSL: {dsl}")

            if config.num_outputs <= 0:
                raise ValueError("num_outputs must be > 0")
            if config.max_models <= 0:
                raise ValueError("max_models must be > 0")

            seed_files = sorted(in_dir.rglob("*.smt2"))
            if len(seed_files) < 2:
                raise ValueError(f"Need at least 2 .smt2 seed files in {in_dir}, found {len(seed_files)}")

            yy_config = config.yinyang_config or "third_party/yinyang/yinyang/config/fusion_functions.txt"
            config_path = Path(yy_config)
            if not config_path.is_absolute():
                config_path = solver_root / config_path
            if not config_path.is_file():
                raise ValueError(f"unable to locate YinYang config at '{config_path}'")

            config_copy_path = out_dir / f"yinyang_config{config_path.suffix or '.txt'}"
            shutil.copy2(config_path, config_copy_path)

            rng = random.Random(seed if seed is not None else 0)
            args = SimpleNamespace(config=str(config_path), oracle=config.oracle)
            limit = config.max_attempts if config.max_attempts is not None else 50 * config.num_outputs
            if limit <= 0:
                raise ValueError("max_attempts must be > 0 when provided")

            manifest_rows: list[dict[str, object]] = []
            seed_inputs_cache: dict[Path, list[str]] = {}
            generated = 0
            attempts = 0
            skipped = 0
            failed = 0

            while generated < config.num_outputs and attempts < limit:
                attempts += 1
                left, right = rng.sample(seed_files, 2)
                script1, _ = parse_file(str(left), silent=True)
                script2, _ = parse_file(str(right), silent=True)
                if script1 is None or script2 is None:
                    failed += 1
                    continue

                # Seed global random because SemanticFusion uses random module internally.
                random.seed(rng.randint(0, 2**31 - 1))
                mutator = SemanticFusion(script1, script2, args)
                mutant, success, skip_seed = mutator.mutate()
                if not success or skip_seed:
                    skipped += 1
                    continue

                smt_text = str(mutant)
                try:
                    dsl_text, extension = translate_smtlib2_to_dsl(smt_text, config.dsl)
                except Exception:
                    failed += 1
                    continue

                solve_result, solve_models = run_smt_solver_models(smt_text, solver="z3", max_models=config.max_models)
                if solve_result != "sat" or not solve_models:
                    failed += 1
                    continue

                if left not in seed_inputs_cache:
                    left_circuit = parse_smtlib2_core(left.read_text())
                    seed_inputs_cache[left] = [v.name for v in left_circuit.inputs]
                if right not in seed_inputs_cache:
                    right_circuit = parse_smtlib2_core(right.read_text())
                    seed_inputs_cache[right] = [v.name for v in right_circuit.inputs]

                model_payloads: list[dict[str, object]] = []
                for model in solve_models:
                    assignments: dict[str, object] = {}
                    for name in seed_inputs_cache[left]:
                        prefixed = f"scr1_{name}"
                        val = model.get(prefixed)
                        if val is not None:
                            assignments[prefixed] = val
                    for name in seed_inputs_cache[right]:
                        prefixed = f"scr2_{name}"
                        val = model.get(prefixed)
                        if val is not None:
                            assignments[prefixed] = val
                    model_payloads.append(
                        {
                            "assignments": assignments,
                            "fused_assignments": {
                                name: val for name, val in model.items() if name.endswith("_fused")
                            },
                        }
                    )

                generated += 1
                stem = f"fused_{generated:04d}"
                smt_path = out_smt_dir / f"{stem}.smt2"
                if config.dsl == "noir":
                    dsl_project_dir = out_dsl_dir / stem
                    package_name = _sanitize_noir_package_name(stem)
                    _write_noir_project(dsl_project_dir, package_name, dsl_text)
                    dsl_path = dsl_project_dir / "src" / "main.nr"
                else:
                    dsl_path = out_dsl_dir / f"{stem}{extension}"
                    dsl_path.write_text(dsl_text)
                solution_path = out_sol_dir / f"{stem}.json"
                smt_path.write_text(smt_text)
                solution_payload = {
                    "result": solve_result,
                    "seed_left": str(left),
                    "seed_right": str(right),
                    "max_models_requested": config.max_models,
                    "model_count": len(model_payloads),
                    "models": model_payloads,
                }
                # Backward compatibility: keep first model flattened at top-level.
                solution_payload["assignments"] = model_payloads[0]["assignments"]
                solution_payload["fused_assignments"] = model_payloads[0]["fused_assignments"]
                solution_path.write_text(json.dumps(solution_payload, indent=2))
                manifest_rows.append(
                    {
                        "index": generated,
                        "attempt": attempts,
                        "seed_left": str(left),
                        "seed_right": str(right),
                        "smt_path": str(smt_path),
                        "dsl_path": str(dsl_path),
                        "solution_path": str(solution_path),
                    }
                )

            manifest = {
                "dsl": config.dsl,
                "format": "circuzz",
                "seed": seed if seed is not None else 0,
                "oracle": config.oracle,
                "config": str(config_path),
                "config_copy": str(config_copy_path),
                "in_dir": str(in_dir),
                "out_dir": str(out_dir),
                "solutions_dir": str(out_sol_dir),
                "solution_solver": "z3",
                "max_models_per_output": config.max_models,
                "num_outputs_requested": config.num_outputs,
                "num_outputs_generated": generated,
                "attempts": attempts,
                "skipped": skipped,
                "failed": failed,
                "generated_at": datetime.now(UTC).isoformat(),
                "outputs": manifest_rows,
            }
            (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

            if generated < config.num_outputs:
                raise RuntimeError(
                    f"Generated {generated}/{config.num_outputs} before reaching max attempts ({limit}). "
                    f"See {out_dir / 'manifest.json'}."
                )

            # build stable result from written solutions (single source of truth)
            stable_programs: list[SMTFusionProgram] = []
            for row in manifest_rows:
                dsl_path = Path(str(row["dsl_path"]))
                solution_path = Path(str(row["solution_path"]))
                if not dsl_path.is_absolute():
                    dsl_path = out_dir / dsl_path
                if not solution_path.is_absolute():
                    solution_path = out_dir / solution_path
                solution_obj = json.loads(solution_path.read_text())
                models_raw = solution_obj.get("models", [])
                models: list[dict[str, int | bool]] = []
                for model in models_raw:
                    assignments = model.get("assignments", {})
                    normalized: dict[str, int | bool] = {}
                    for name, value in assignments.items():
                        if isinstance(value, bool):
                            normalized[name] = value
                        elif isinstance(value, int):
                            normalized[name] = value
                        elif isinstance(value, str):
                            low = value.lower()
                            if low == "true":
                                normalized[name] = True
                            elif low == "false":
                                normalized[name] = False
                            else:
                                normalized[name] = int(value)
                        else:
                            raise ValueError(f"unsupported model assignment value type: {type(value)}")
                    models.append(normalized)
                stable_programs.append(
                    SMTFusionProgram(
                        name=dsl_path.stem,
                        dsl_path=dsl_path,
                        solution_path=solution_path,
                        models=models,
                    )
                )

            if len(stable_programs) == 0:
                raise RuntimeError("smt fusion produced no programs")
            return stable_programs
