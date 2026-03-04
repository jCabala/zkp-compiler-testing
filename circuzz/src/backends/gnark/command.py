from circuzz.common.command import execute_command
from circuzz.common.command import ExecStatus

from pathlib import Path
import shutil

_GO_TEST_CALL_COUNT = 0
_GO_CACHE_CLEAN_INTERVAL = 1000

def go_test(working_dir: Path, go_test_timeout: str | None, verbose: bool = False) -> ExecStatus:
    global _GO_TEST_CALL_COUNT
    assert shutil.which("go"), "Unable to find 'go' in PATH!"
    command = [shutil.which("go"), "test"]
    if verbose:
        command += ["-v"]
    if go_test_timeout != None:
        command += ["-timeout", go_test_timeout]
    result = execute_command(command, "go-test", working_dir=working_dir)
    _GO_TEST_CALL_COUNT += 1
    # Each circuit is unique so cached build artefacts are never reused across
    # iterations. Periodically clean the cache to prevent unbounded disk growth
    # over long experiments while keeping gnark library packages warm between cleans.
    if _GO_TEST_CALL_COUNT % _GO_CACHE_CLEAN_INTERVAL == 0:
        go = shutil.which("go")
        if go:
            execute_command([go, "clean", "-cache"], "go-clean-cache", working_dir=working_dir)
    return result
