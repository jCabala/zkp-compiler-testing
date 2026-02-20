from pathlib import Path
import shutil

from circuzz.common.command import ExecStatus
from circuzz.common.command import execute_command

#
# nargo, noir executer and compiler
#


def noir_execute(
    working_dir: Path,
    witness_name: str,
    expr_width: int = 4,
    inliner_aggressiveness: int | None = None,
) -> ExecStatus:
    assert shutil.which("nargo"), "Unable to find 'nargo' in PATH!"
    command = \
        [ shutil.which("nargo")
        , "execute"
        , "--silence-warnings"
        , "--force"
        , witness_name
        # , "--expression-width", str(expr_width)  # Not supported in nargo 0.38.0 and similar versions
        # NOTE: --expression-width flag is commented out because it's not supported in all nargo versions.
        # Some versions (e.g., 0.38.0) reject this flag with "unexpected argument" error.
        # If using a newer version that supports this flag, uncomment the lines below.  
        ]
    if inliner_aggressiveness is not None:
        command += ["--inliner-aggressiveness", str(inliner_aggressiveness)]
    return execute_command(command, "noir-execute", working_dir)


#
# Get current version
#

def noir_version() -> ExecStatus:
    assert shutil.which("nargo"), "Unable to find 'nargo' in PATH!"
    command = [shutil.which("nargo"), "--version"]
    return execute_command(command, "noir-version")

#
# bb prover and verifier
#

def bb_prove(noir_json: Path, witness_gz: Path, proof: Path, vk: Path | None = None) -> ExecStatus:
    assert shutil.which("bb"), "Unable to find 'bb' in PATH!"
    command = \
        [ shutil.which("bb")
        , "prove"
        , "-b", noir_json.as_posix()
        , "-w", witness_gz.as_posix()
        , "-o", proof.as_posix()
        # Reduce prover memory pressure in newer bb/ultra_honk toolchains.
        , "--slow_low_memory"
        , "--storage_budget", "512m"
        ]
    if vk is not None:
        command.extend(["-k", vk.as_posix()])
    return execute_command(command, "noir-bb-prove")


def bb_write_vk(noir_json: Path, vk: Path) -> ExecStatus:
    assert shutil.which("bb"), "Unable to find 'bb' in PATH!"
    command = \
        [ shutil.which("bb")
        , "write_vk"
        , "-b", noir_json.as_posix()
        , "-o", vk.as_posix()
        ]
    return execute_command(command, "noir-bb-write-vk")


def bb_verify(vk: Path, proof: Path) -> ExecStatus:
    assert shutil.which("bb"), "Unable to find 'bb' in PATH!"
    command = \
        [ shutil.which("bb")
        , "verify"
        , "-k", vk.as_posix()
        , "-p", proof.as_posix()
        ]
    return execute_command(command, "noir-bb-verify")
