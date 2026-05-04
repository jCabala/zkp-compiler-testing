from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli.helper_tools_cli.translate_dsl import translate_smtlib2_to_dsl


def test_fused_output_uses_unconstrained_helper():
    smtlib2 = """
(set-logic QF_FF)
(define-sort F () (_ FiniteField 101))
(declare-fun scr1_x1 () F)
(declare-fun scr2_x2 () F)
(declare-fun scr1_x1_scr2_x2_fused () F)
(assert (= scr1_x1 (as ff1 F)))
(assert (= scr2_x2 (as ff1 F)))
(check-sat)
""".strip()

    noir_source, extension = translate_smtlib2_to_dsl(smtlib2, "noir")

    assert extension == ".nr"
    assert "unconstrained fn scr1_x1_scr2_x2_fused_hint" in noir_source
    assert "// Safety: the hinted fused output is intentionally unconstrained and only used as a witness." in noir_source
    assert "unsafe { scr1_x1_scr2_x2_fused_hint(scr1_x1, scr2_x2) }" in noir_source
    assert "fused_scr1_x1_scr2_x2_fused" not in noir_source
