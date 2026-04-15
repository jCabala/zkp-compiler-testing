from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import json
import os
import subprocess
import tempfile


PROPERLY_CONSTRAINED_MSG = "The circuit is properly constrained"
UNDERCONSTRAINED_MSG = "The circuit is underconstrained"
PICUS_CIRCOM_OPT_LEVEL = "2"

class PicusResultType:
    PROPERLY_CONSTRAINED = "properly_constrained"
    UNDERCONSTRAINED = "underconstrained"
    UNKNOWN = "unknown"
    ERROR = "error"

@dataclass
class PicusResult:
    result: PicusResultType
    exit_code: int
    output: str


def _write_precondition_json(hints: Dict[int, int]) -> Path:
    """Write a Picus precondition JSON file from wire_index -> value hints."""
    entries = []
    for wire_idx, value in hints.items():
        entry = ["hint", ["rassert", ["req", ["rvar", wire_idx], ["rint", value]]]]
        entries.append(entry)

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="picus-hints-", delete=False
    )
    json.dump(entries, tmp)
    tmp.close()
    return Path(tmp.name)


def solve_picus(input_path: Path, hints: Optional[Dict[int, int]] = None, solving_timeout: Optional[int] = None) -> PicusResult:
    picus_script = Path("~/Picus/run-picus").expanduser()

    cmd = [str(picus_script)]
    if input_path.suffix == ".circom":
        cmd += ["--opt-level", PICUS_CIRCOM_OPT_LEVEL]

    precondition_path = None
    if hints:
        precondition_path = _write_precondition_json(hints)
        cmd += ["--precondition", str(precondition_path)]

    cmd.append(str(input_path))

    try:
        env = dict(
            os.environ,
            TMPDIR=tempfile.gettempdir(),
            TMP=tempfile.gettempdir(),
            TEMP=tempfile.gettempdir(),
        )
        cmd_result = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=solving_timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return PicusResult(result=PicusResultType.UNKNOWN, exit_code=-1, output="")
    finally:
        if precondition_path and precondition_path.exists():
            precondition_path.unlink()

    # Picus exit codes are semantic:
    #   8 => safe/properly constrained
    #   9 => unsafe/underconstrained
    #   0 => unknown
    has_properly_constrained_msg = PROPERLY_CONSTRAINED_MSG in cmd_result.stdout
    has_underconstrained_msg = UNDERCONSTRAINED_MSG in cmd_result.stdout

    if cmd_result.returncode == 8 and has_properly_constrained_msg:
        result = PicusResultType.PROPERLY_CONSTRAINED
    elif cmd_result.returncode == 9 and has_underconstrained_msg:
        result = PicusResultType.UNDERCONSTRAINED
    elif cmd_result.returncode == 0 and not has_properly_constrained_msg and not has_underconstrained_msg:
        result = PicusResultType.UNKNOWN
    else:
        result = PicusResultType.ERROR

    return PicusResult(
        result=result,
        exit_code=cmd_result.returncode,
        output=cmd_result.stdout,
    )
