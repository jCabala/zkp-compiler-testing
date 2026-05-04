from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backends.noir.acir_to_r1cs import BN254_FR_PRIME, build_r1cs_from_decoded_noir_acir


def _decoded_with_asserts(*assert_texts: str) -> dict:
    opcodes = [{"index": idx, "kind": "ASSERT", "text": text} for idx, text in enumerate(assert_texts)]
    return {
        "inspector_output": {
            "functions": [
                {
                    "name": "main",
                    "private_parameters": ["w0", "w1"],
                    "public_parameters": [],
                    "return_values": ["w2"],
                    "opcodes": opcodes,
                }
            ]
        }
    }


def test_acir_asserts_preserve_input_output_split():
    translation = build_r1cs_from_decoded_noir_acir(
        _decoded_with_asserts(
            "ASSERT w0 = 1",
            "ASSERT w2 = w0 + w1",
        )
    )

    assert translation.input_wires == [1, 2]
    assert translation.output_wires == [3]
    assert translation.witness_map == {"w0": 1, "w1": 2, "w2": 3}
    assert translation.r1cs.nPrvInputs == 2
    assert translation.r1cs.nOutputs == 1
    assert translation.r1cs.nConstraints == 2


def test_acir_multi_quadratic_assert_splits_into_multiple_r1cs_rows():
    translation = build_r1cs_from_decoded_noir_acir(
        _decoded_with_asserts(
            "ASSERT 0 = w0*w1 + w1*w2 + w0 + 3",
        )
    )

    assert translation.r1cs.nConstraints == 3
    assert translation.r1cs.nVars == 6

    first, second, final = translation.r1cs.constraints
    neg_one = BN254_FR_PRIME - 1
    assert [(term.coeff, term.variable.index) for term in first.A.terms] == [(neg_one, 1)]
    assert [(term.coeff, term.variable.index) for term in first.B.terms] == [(1, 2)]
    assert [(term.coeff, term.variable.index) for term in first.C.terms] == [(1, 4)]

    assert [(term.coeff, term.variable.index) for term in second.A.terms] == [(neg_one, 2)]
    assert [(term.coeff, term.variable.index) for term in second.B.terms] == [(1, 3)]
    assert [(term.coeff, term.variable.index) for term in second.C.terms] == [(1, 5)]

    final_terms = {(term.variable.index, term.coeff) for term in final.A.terms}
    assert (0, BN254_FR_PRIME - 3) in final_terms
    assert (1, BN254_FR_PRIME - 1) in final_terms
    assert (4, 1) in final_terms
    assert (5, 1) in final_terms
    assert [(term.coeff, term.variable.index) for term in final.B.terms] == [(1, 0)]
    assert final.C.terms == []
