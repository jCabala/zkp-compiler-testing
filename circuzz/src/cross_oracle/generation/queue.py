from __future__ import annotations

import json
import random
import shutil
from pathlib import Path
from typing import Any

from cross_oracle.adapters.base import FusionGeneratorBackend
from cross_oracle.generation.runner import run_smt_fusion_generation
from cross_oracle.generation.types import SMTFusionProgram, SMTFusionRunConfig

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


def _cleanup_old_batch_dirs(state_dir: Path, keep_batch_id: int | None) -> None:
    for candidate in state_dir.glob("batch_*"):
        if not candidate.is_dir():
            continue
        suffix = candidate.name.removeprefix("batch_")
        if not suffix.isdigit():
            continue
        batch_id = int(suffix)
        if keep_batch_id is not None and batch_id == keep_batch_id:
            continue
        shutil.rmtree(candidate, ignore_errors=True)


def next_smt_fusion_program(
    state_root_dir: Path,
    config: SMTFusionRunConfig,
    run_seed: float,
    backend: FusionGeneratorBackend | None = None,
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
        programs = run_smt_fusion_generation(batch_dir, config, seed=fusion_seed, backend=backend)
        state["batch_id"] = batch_id
        state["fusion_seed"] = fusion_seed
        state["next_index"] = 0
        state["programs"] = [_program_to_json_row(program) for program in programs]
        state_path.write_text(json.dumps(state, indent=2))

    active_batch_id = int(state.get("batch_id", -1))
    _cleanup_old_batch_dirs(state_dir, active_batch_id if active_batch_id >= 0 else None)

    index = int(state.get("next_index", 0))
    program_rows = state.get("programs", [])
    if not isinstance(program_rows, list) or index >= len(program_rows):
        raise RuntimeError("invalid SMT fusion queue state")

    selected = _program_from_json_row(dict(program_rows[index]))
    state["next_index"] = index + 1
    state_path.write_text(json.dumps(state, indent=2))
    return selected
