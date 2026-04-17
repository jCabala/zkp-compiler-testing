from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[3]
YINYANG_ROOT = ROOT / "smt-solver" / "third_party" / "yinyang"

if str(ROOT / "smt-solver") not in sys.path:
	sys.path.insert(0, str(ROOT / "smt-solver"))
if str(YINYANG_ROOT) not in sys.path:
	sys.path.insert(0, str(YINYANG_ROOT))

from yinyang.src.mutators.SemanticFusion.SemanticFusion import SemanticFusion
from yinyang.src.parsing.Parse import parse_file, parse_str


FF_FORMULA = """(set-logic QF_FF)
(define-sort F () (_ FiniteField 17))
(declare-fun v1 () F)
(assert (= (ff.mul v1 v1) v1))
(assert (= (ff.add v1 (as ff1 F)) (as ff0 F)))
(check-sat)
"""


def test_yinyang_parses_qf_ff_with_as_constants(tmp_path: Path):
	path = tmp_path / "seed.smt2"
	path.write_text(FF_FORMULA)

	script, globs = parse_file(str(path), silent=False)

	assert script is not None
	assert globs is not None
	assert "v1" in globs
	assert globs["v1"] == "F"


def test_yinyang_semantic_fusion_supports_ff_templates():
	script1, _ = parse_str(FF_FORMULA, silent=False)
	script2, _ = parse_str(FF_FORMULA.replace("v1", "w1"), silent=False)

	args = SimpleNamespace(
		config=str(ROOT / "smt-solver" / "experiments" / "legacy" / "sat_fusion" / "sat_fusion_config.txt"),
		oracle="sat",
	)
	mutator = SemanticFusion(script1, script2, args)

	assert "F" in mutator.templates

	mutant, success, skip_seed = mutator.mutate()

	assert success is True
	assert skip_seed is False
	text = str(mutant)
	assert "_fused" in text
	assert "ff.add" in text
