from dataclasses import dataclass
from pathlib import Path
import subprocess


PROPERLY_CONSTRAINED_MSG = "The circuit is properly constrained"
UNDERCONSTRAINED_MSG = "The circuit is underconstrained"

class PicusResultType:
    PROPERLY_CONSTRAINED = "properly_constrained"
    UNDERCONSTRAINED = "underconstrained"
    UNKNOWN = "unknown"

@dataclass
class PicusResult:
    result: PicusResultType


def solve_picus(input_path: Path) -> PicusResult:
    picus_script = Path("~/Picus/run-picus").expanduser()

    cmd_result = subprocess.run(
        [str(picus_script), str(input_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    result = PicusResultType.UNKNOWN
    if PROPERLY_CONSTRAINED_MSG in cmd_result.stdout:
        result = PicusResultType.PROPERLY_CONSTRAINED
    elif UNDERCONSTRAINED_MSG in cmd_result.stdout:
        result = PicusResultType.UNDERCONSTRAINED

    # Placeholder: you can later infer this from output / exit code
    return PicusResult(result=result)
