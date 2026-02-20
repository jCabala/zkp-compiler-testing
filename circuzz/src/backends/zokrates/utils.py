# ==============================
# backends/zokrates/utils.py
# ==============================
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from random import Random
from circuzz.common.field import CurvePrime

class ZokratesCurve(StrEnum):
    BN254 = "bn254"
    BLS12_381 = "bls12_381"

def curve_to_prime(curve: ZokratesCurve) -> CurvePrime:
    # map onto your existing CurvePrime enum/values
    match curve:
        case ZokratesCurve.BN254:
            return CurvePrime.BN254
        case ZokratesCurve.BLS12_381:
            return CurvePrime.BLS12_381
        case _:
            raise NotImplementedError(curve)

@dataclass
class IterationSetting:
    input_map: dict[str, int]
    do_prove_verify: int = 0

# Metamorphic relation checker hook:
# to avoid importing gnark utils, we provide a tiny adapter.
class _RelationChecker:
    def check_relation(self, relation, c1_outputs: list[int], c2_outputs: list[int]) -> tuple[bool, str | None]:
        # You already encode relation semantics in your tooling somewhere.
        # Plug it here: return (True, None) if OK, else (False, "reason").
        #
        # Minimal default: equality of full output vector.
        if c1_outputs == c2_outputs:
            return True, None
        return False, "outputs differ"

write_test_func_to_buffer = _RelationChecker()
