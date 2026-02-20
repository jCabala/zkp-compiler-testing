from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from circuzz.common.command import execute_command
from circuzz.common.filesystem import clean_or_create_dir


@dataclass(frozen=True)
class SMTFusionRunConfig:
    smt_solver_path: str
    smt_seed_dir: str
    dsl: str
    num_outputs: int
    max_models: int
    yinyang_config: str | None
    oracle: str
    max_attempts: int | None


@dataclass(frozen=True)
class SMTFusionProgram:
    name: str
    dsl_path: Path
    solution_path: Path
    models: list[dict[str, int | bool]]


_FUSION_SEED_MODULUS = 2_147_483_647


def _normalize_assignment_value(value: Any) -> int | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        low = value.lower()
        if low == "true":
            return True
        if low == "false":
            return False
        return int(value)
    raise ValueError(f"unsupported model assignment value type: {type(value)}")


def _resolve_generated_path(base_dir: Path, path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return base_dir / p


def run_smt_fusion_generation(
    working_dir: Path,
    config: SMTFusionRunConfig,
    seed: int | None = None,
) -> list[SMTFusionProgram]:
    solver_root = Path(config.smt_solver_path)
    cli_path = solver_root / "cli.py"
    if not cli_path.is_file():
        raise ValueError(f"unable to locate smt-solver CLI at '{cli_path}'")

    in_dir = Path(config.smt_seed_dir)
    if not in_dir.is_absolute():
        in_dir = solver_root / in_dir
    if not in_dir.is_dir():
        raise ValueError(f"unable to locate SMT seed directory '{in_dir}'")

    out_dir = working_dir / "smt_fusion"
    clean_or_create_dir(out_dir)

    command = [
        sys.executable,
        str(cli_path),
        "fuse-smt-to-dsl",
        str(in_dir),
        str(out_dir),
        "--dsl",
        config.dsl,
        "--num-outputs",
        str(config.num_outputs),
        "--max-models",
        str(config.max_models),
        "--format",
        "circuzz",
        "--oracle",
        config.oracle,
    ]
    if seed is not None:
        command += ["--seed", str(seed)]
    if config.yinyang_config is not None:
        config_path = Path(config.yinyang_config)
        if not config_path.is_absolute():
            config_path = solver_root / config_path
        command += ["--config", str(config_path)]
    if config.max_attempts is not None:
        command += ["--max-attempts", str(config.max_attempts)]

    # smt-solver vendors YinYang under third_party/yinyang; add it to PYTHONPATH
    # so imports like `import yinyang.src...` work reliably in container runs.
    yinyang_root = solver_root / "third_party" / "yinyang"
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath_parts = [str(yinyang_root)]
    if current_pythonpath != "":
        pythonpath_parts.append(current_pythonpath)
    run_env = {"PYTHONPATH": os.pathsep.join(pythonpath_parts)}

    status = execute_command(command, "smt-fusion-generate", env=run_env)
    if status.returncode != 0:
        raise RuntimeError(f"smt fusion generation failed: {status.stderr or status.stdout}")

    manifest_path = out_dir / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"missing fusion manifest at '{manifest_path}'")
    manifest = json.loads(manifest_path.read_text())

    outputs = manifest.get("outputs", [])
    programs: list[SMTFusionProgram] = []
    for row in outputs:
        dsl_path = _resolve_generated_path(out_dir, str(row["dsl_path"]))
        solution_path = _resolve_generated_path(out_dir, str(row["solution_path"]))
        if not dsl_path.exists():
            raise RuntimeError(f"missing generated DSL source '{dsl_path}'")
        if not solution_path.is_file():
            raise RuntimeError(f"missing generated solution file '{solution_path}'")

        solution_obj = json.loads(solution_path.read_text())
        models_raw = solution_obj.get("models", [])
        models: list[dict[str, int | bool]] = []
        for model in models_raw:
            assignments = model.get("assignments", {})
            normalized = {
                name: _normalize_assignment_value(value)
                for name, value in assignments.items()
            }
            models.append(normalized)

        if len(models) == 0:
            raise RuntimeError(f"no models found in solution file '{solution_path}'")

        programs.append(
            SMTFusionProgram(
                name=dsl_path.stem,
                dsl_path=dsl_path,
                solution_path=solution_path,
                models=models,
            )
        )

    if len(programs) == 0:
        raise RuntimeError("smt fusion produced no programs")
    return programs


def _run_seed_to_int(run_seed: float) -> int:
    raw = int(abs(run_seed) * 1_000_000_000)
    return raw % _FUSION_SEED_MODULUS


def _program_to_json_row(program: SMTFusionProgram) -> dict[str, object]:
    return {
        "name": program.name,
        "dsl_path": str(program.dsl_path),
        "solution_path": str(program.solution_path),
        "models": program.models,
    }


def _program_from_json_row(row: dict[str, Any]) -> SMTFusionProgram:
    models: list[dict[str, int | bool]] = []
    for model in row.get("models", []):
        assignments = {
            str(name): _normalize_assignment_value(value)
            for name, value in dict(model).items()
        }
        models.append(assignments)

    return SMTFusionProgram(
        name=str(row["name"]),
        dsl_path=Path(str(row["dsl_path"])),
        solution_path=Path(str(row["solution_path"])),
        models=models,
    )


def _state_programs_exist(state: dict[str, Any]) -> bool:
    rows = state.get("programs", [])
    if not isinstance(rows, list) or len(rows) == 0:
        return False
    for row in rows:
        dsl_path = Path(str(row.get("dsl_path", "")))
        solution_path = Path(str(row.get("solution_path", "")))
        if not dsl_path.exists() or not solution_path.is_file():
            return False
    return True


def _ensure_rng_state(state: dict[str, Any], run_seed: float) -> None:
    if "rng_seed" in state and "rng_draw_count" in state:
        return
    base_seed = _run_seed_to_int(run_seed)
    # Migration path from older state format:
    # skip already-consumed/used batches so the next generated batch advances.
    batch_id = int(state.get("batch_id", -1))
    state["rng_seed"] = base_seed
    state["rng_draw_count"] = max(0, batch_id + 1)


def _next_fusion_seed_from_state(state: dict[str, Any]) -> int:
    rng_seed = int(state["rng_seed"])
    draw_count = int(state["rng_draw_count"])
    rng = random.Random(rng_seed)
    for _ in range(draw_count):
        rng.randrange(_FUSION_SEED_MODULUS)
    fusion_seed = rng.randrange(_FUSION_SEED_MODULUS)
    state["rng_draw_count"] = draw_count + 1
    return fusion_seed


def next_smt_fusion_program(
    state_root_dir: Path,
    config: SMTFusionRunConfig,
    run_seed: float,
) -> SMTFusionProgram:
    """
    Returns one program from a persistent SMT-fusion batch queue.
    A new batch is generated only after all programs from the current batch
    have been consumed.
    """
    state_dir = state_root_dir / ".smt_fusion_queue" / config.dsl
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"

    state: dict[str, Any] | None = None
    if state_path.is_file():
        state = json.loads(state_path.read_text())

    if state is None:
        state = {
            "batch_id": -1,
            "next_index": 0,
            "programs": [],
            "rng_seed": _run_seed_to_int(run_seed),
            "rng_draw_count": 0,
        }
    else:
        _ensure_rng_state(state, run_seed)

    need_new_batch = (
        state is None
        or not _state_programs_exist(state)
        or int(state.get("next_index", 0)) >= len(state.get("programs", []))
    )

    if need_new_batch:
        prev_batch_id = int(state.get("batch_id", -1))
        batch_id = prev_batch_id + 1
        fusion_seed = _next_fusion_seed_from_state(state)
        batch_dir = state_dir / f"batch_{batch_id:06d}"
        programs = run_smt_fusion_generation(batch_dir, config, seed=fusion_seed)
        state["batch_id"] = batch_id
        state["fusion_seed"] = fusion_seed
        state["next_index"] = 0
        state["programs"] = [_program_to_json_row(program) for program in programs]
        state_path.write_text(json.dumps(state, indent=2))

    index = int(state.get("next_index", 0))
    program_rows = state.get("programs", [])
    if not isinstance(program_rows, list) or index >= len(program_rows):
        raise RuntimeError("invalid SMT fusion queue state")

    selected = _program_from_json_row(dict(program_rows[index]))
    state["next_index"] = index + 1
    state_path.write_text(json.dumps(state, indent=2))
    return selected
