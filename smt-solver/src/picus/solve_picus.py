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

    # Picus exit codes are semantic:
    #   8 => safe/properly constrained
    #   9 => unsafe/underconstrained
    #   0 => unknown
    # We require both exit code and expected message for strict classification.
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
