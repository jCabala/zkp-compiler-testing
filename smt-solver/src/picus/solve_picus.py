from dataclasses import dataclass
from pathlib import Path
import subprocess


PROPERLY_CONSTRAINED_MSG = "The circuit is properly constrained"
UNDERCONSTRAINED_MSG = "The circuit is underconstrained"

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


def solve_picus(input_path: Path) -> PicusResult:
    picus_script = Path("~/Picus/run-picus").expanduser()

    cmd_result = subprocess.run(
        [str(picus_script), str(input_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if cmd_result.returncode != 0:
        return PicusResult(
            result=PicusResultType.ERROR,
            exit_code=cmd_result.returncode,
            output=cmd_result.stdout,
        )

    result = PicusResultType.UNKNOWN
    if PROPERLY_CONSTRAINED_MSG in cmd_result.stdout:
        result = PicusResultType.PROPERLY_CONSTRAINED
    elif UNDERCONSTRAINED_MSG in cmd_result.stdout:
        result = PicusResultType.UNDERCONSTRAINED

    return PicusResult(
        result=result,
        exit_code=cmd_result.returncode,
        output=cmd_result.stdout,
    )
