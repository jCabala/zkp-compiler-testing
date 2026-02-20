from enum import StrEnum


DOCKER_GLOBAL_CIRCOMLIB_CIRCUITS_PATH = "/circuzz/circomlib/circuits/"
LOCAL_NODE_MODULES_CIRCOMLIB_CIRCUITS_PATH = "./node_modules/circomlib/circuits/"
COMPARATORS_FILE_PATH = "comparators.circom"

class LibPathMode(StrEnum):
    DOCKER_GLOBAL = "DOCKER_GLOBAL"
    LOCAL         = "LOCAL"
    

class LibPathResolver:

    def __init__(self, mode: LibPathMode):
        self.mode = mode

    def get_path_prefix(self) -> str:
        if self.mode == LibPathMode.LOCAL:
            return LOCAL_NODE_MODULES_CIRCOMLIB_CIRCUITS_PATH

        return DOCKER_GLOBAL_CIRCOMLIB_CIRCUITS_PATH

    def get_comparators_path(self) -> str:
            if self.mode == LibPathMode.LOCAL:
                return LOCAL_NODE_MODULES_CIRCOMLIB_CIRCUITS_PATH + COMPARATORS_FILE_PATH

            return DOCKER_GLOBAL_CIRCOMLIB_CIRCUITS_PATH + COMPARATORS_FILE_PATH