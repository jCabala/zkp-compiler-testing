from dataclasses import dataclass
from random import Random
from typing import Any
from enum import StrEnum
import json
from pathlib import Path

from circuzz.common.probability import bernoulli
from circuzz.ir.config import IRConfig

from backends.circom.config import CircomConfig
from backends.corset.config import CorsetConfig
from backends.gnark.config import GnarkConfig
from backends.noir.config import NoirConfig
from backends.mina.config import MinaConfig
from backends.zokrates.ir2zokrates import ZokratesConfig


#
# Online Tuning
#

class TuningStrategy(StrEnum):
    NEVER = "never"
    ALWAYS = "always"
    TIME = "time"
    EXECUTION = "execution"
    LIKELIHOOD = "likelihood"

    @classmethod
    def from_str(cls, value: str) -> 'TuningStrategy':
        match value:
            case "never":
                return TuningStrategy.NEVER
            case "always":
                return TuningStrategy.ALWAYS
            case "time":
                return TuningStrategy.TIME
            case "execution":
                return TuningStrategy.EXECUTION
            case "likelihood":
                return TuningStrategy.LIKELIHOOD
            case _:
                raise NotImplementedError(
                    f"unimplemented tuning strategy '{value}', try {list(TuningStrategy)}"
                )


@dataclass()
class OnlineTuning():

    prove_and_verify_target_percentage: float = 0
    prove_and_verify_tuning_strategy: TuningStrategy = TuningStrategy.ALWAYS

    overall_execution_time: float = 0
    prove_and_verify_time: float = 0
    prove_and_verify_ticks: int = 0
    prove_and_verify_exec: int = 0

    def is_prove_and_verify(self, rng: Random) -> bool:
        match self.prove_and_verify_tuning_strategy:
            case TuningStrategy.ALWAYS:
                return True
            case TuningStrategy.NEVER:
                return False
            case TuningStrategy.TIME:
                available_time = (
                    self.overall_execution_time * self.prove_and_verify_target_percentage
                )
                return self.prove_and_verify_time < available_time
            case TuningStrategy.EXECUTION:
                available_exec = (
                    self.prove_and_verify_ticks * self.prove_and_verify_target_percentage
                )
                return self.prove_and_verify_exec < available_exec
            case TuningStrategy.LIKELIHOOD:
                return bernoulli(self.prove_and_verify_target_percentage, rng)
            case _:
                raise NotImplementedError(
                    f"unknown strategy {self.prove_and_verify_tuning_strategy}"
                )

    def set_prove_and_verify_tuning(
        self,
        strategy: TuningStrategy,
        percentage: float | None = None,
    ):
        if percentage is None:
            percentage = 0
        assert 0 <= percentage <= 1
        self.prove_and_verify_tuning_strategy = strategy
        self.prove_and_verify_target_percentage = percentage

    def add_general_execution_time(self, exec_time: float):
        self.overall_execution_time += exec_time

    def add_prove_or_verify_time(self, exec_time: float):
        self.overall_execution_time += exec_time
        self.prove_and_verify_time += exec_time

    def inc_prove_and_verify_ticks(self):
        self.prove_and_verify_ticks += 1

    def inc_prove_and_verify_exec(self):
        self.prove_and_verify_exec += 1


#
# Experiment configuration
#

@dataclass(frozen=True)
class ExperimentConfig:
    enable_exit_on_failure: bool
    enable_working_dir_cleanup: bool

    prove_and_verify_tuning_strategy: TuningStrategy
    prove_and_verify_tuning_percentage: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'ExperimentConfig':
        enable_exit_on_failure = value.get("enable_exit_on_failure", True) is True
        enable_working_dir_cleanup = value.get("enable_working_dir_cleanup", True) is True

        strategy_str = value.get("prove_and_verify_tuning_strategy", "always")
        strategy = TuningStrategy.from_str(strategy_str)

        if strategy in {TuningStrategy.LIKELIHOOD, TuningStrategy.TIME}:
            if "prove_and_verify_tuning_percentage" not in value:
                raise ValueError(
                    "missing 'prove_and_verify_tuning_percentage' required by "
                    f"strategy '{strategy_str}'"
                )

        percentage = value.get("prove_and_verify_tuning_percentage", 0)

        return ExperimentConfig(
            enable_exit_on_failure=enable_exit_on_failure,
            enable_working_dir_cleanup=enable_working_dir_cleanup,
            prove_and_verify_tuning_strategy=strategy,
            prove_and_verify_tuning_percentage=percentage,
        )


#
# ZKP Languages
#

class ZKPLanguage(StrEnum):
    CIRCOM   = "circom"
    NOIR     = "noir"
    CORSET   = "corset"
    GNARK    = "gnark"
    MINA     = "mina"
    ZOKRATES = "zokrates"

    @classmethod
    def from_str(cls, value: str) -> 'ZKPLanguage':
        match value:
            case "circom":
                return ZKPLanguage.CIRCOM
            case "noir":
                return ZKPLanguage.NOIR
            case "corset":
                return ZKPLanguage.CORSET
            case "gnark":
                return ZKPLanguage.GNARK
            case "mina":
                return ZKPLanguage.MINA
            case "zokrates":
                return ZKPLanguage.ZOKRATES
            case _:
                raise NotImplementedError(
                    f"unimplemented zkp language '{value}', try {list(ZKPLanguage)}"
                )


#
# Unified Config
#

@dataclass()
class Config:

    zkp_language: ZKPLanguage
    zkp_config: (
        CircomConfig
        | CorsetConfig
        | GnarkConfig
        | NoirConfig
        | MinaConfig
        | ZokratesConfig
    )

    ir: IRConfig
    experiment: ExperimentConfig

    @property
    def circom(self) -> CircomConfig:
        assert self.zkp_language == ZKPLanguage.CIRCOM
        return self.zkp_config  # pyright: ignore

    @property
    def corset(self) -> CorsetConfig:
        assert self.zkp_language == ZKPLanguage.CORSET
        return self.zkp_config  # pyright: ignore

    @property
    def gnark(self) -> GnarkConfig:
        assert self.zkp_language == ZKPLanguage.GNARK
        return self.zkp_config  # pyright: ignore

    @property
    def noir(self) -> NoirConfig:
        assert self.zkp_language == ZKPLanguage.NOIR
        return self.zkp_config  # pyright: ignore

    @property
    def mina(self) -> MinaConfig:
        assert self.zkp_language == ZKPLanguage.MINA
        return self.zkp_config  # pyright: ignore

    @property
    def zokrates(self) -> ZokratesConfig:
        assert self.zkp_language == ZKPLanguage.ZOKRATES
        return self.zkp_config  # pyright: ignore


#
# Loader
#

def load_config_file(path_to_config: Path, language: str) -> Config:
    assert path_to_config.is_file(), \
        f"Unable to load config file at location {path_to_config}"

    json_obj = _load_json_with_extends(path_to_config)

    config_zkp_language = ZKPLanguage.from_str(language)

    if config_zkp_language == ZKPLanguage.CIRCOM and "circom" in json_obj:
        zkp_config = CircomConfig.from_dict(json_obj["circom"])
    elif config_zkp_language == ZKPLanguage.CORSET and "corset" in json_obj:
        zkp_config = CorsetConfig.from_dict(json_obj["corset"])
    elif config_zkp_language == ZKPLanguage.GNARK and "gnark" in json_obj:
        zkp_config = GnarkConfig.from_dict(json_obj["gnark"])
    elif config_zkp_language == ZKPLanguage.NOIR and "noir" in json_obj:
        zkp_config = NoirConfig.from_dict(json_obj["noir"])
    elif config_zkp_language == ZKPLanguage.MINA and "mina" in json_obj:
        zkp_config = MinaConfig.from_dict(json_obj["mina"])
    elif config_zkp_language == ZKPLanguage.ZOKRATES and "zokrates" in json_obj:
        zkp_config = ZokratesConfig.from_dict(json_obj["zokrates"])
    else:
        raise ValueError(
            f"unable to find configuration for '{config_zkp_language}' in {path_to_config}"
        )

    config_ir = IRConfig.from_dict(json_obj["ir"])
    config_experiment = ExperimentConfig.from_dict(json_obj["experiment"])

    return Config(
        zkp_language=config_zkp_language,
        zkp_config=zkp_config,
        ir=config_ir,
        experiment=config_experiment,
    )


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_json_with_extends(path_to_config: Path, stack: set[Path] | None = None) -> dict[str, Any]:
    if stack is None:
        stack = set()

    resolved = path_to_config.resolve()
    if resolved in stack:
        chain = " -> ".join(str(p) for p in [*stack, resolved])
        raise ValueError(f"cyclic config inheritance detected: {chain}")
    stack.add(resolved)

    with open(path_to_config, "r") as fh:
        raw_obj: dict[str, Any] = json.load(fh)

    extends = raw_obj.pop("extends", None)
    if extends is None:
        stack.remove(resolved)
        return raw_obj

    base_paths: list[Path]
    if isinstance(extends, str):
        base_paths = [Path(extends)]
    elif isinstance(extends, list) and all(isinstance(item, str) for item in extends):
        base_paths = [Path(item) for item in extends]
    else:
        raise ValueError("'extends' must be a string or list of strings")

    merged_base: dict[str, Any] = {}
    for base_path in base_paths:
        resolved_base = base_path if base_path.is_absolute() else path_to_config.parent / base_path
        if not resolved_base.is_file():
            raise ValueError(
                f"unable to locate inherited config '{resolved_base}' "
                f"(referenced from '{path_to_config}')"
            )
        parent_obj = _load_json_with_extends(resolved_base, stack)
        merged_base = _merge_dicts(merged_base, parent_obj)

    stack.remove(resolved)
    return _merge_dicts(merged_base, raw_obj)
