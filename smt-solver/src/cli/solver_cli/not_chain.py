"""
NOT chain augmentation for SMT-LIB formulas.

Injects one or more chains of NOT constraints, each anchored to a distinct
randomly chosen variable, enlarging linear clusters in the compiled R1CS to
trigger P4 (Circom simplification threshold: 350 constraints).

Introduced variables use the `_removable_` prefix — the solver layer detects
this prefix in the sym/sr1cs file and eliminates all constraints involving
these wires before building the SMT query. Since the NOT chain is fully
determined by the circuit, dropping its constraints is safe and keeps the
query smaller.

Variable naming: _removable_{chain_idx}_{link_idx}
  e.g. chain 1: _removable_1_1, _removable_1_2, ..., _removable_1_N
       chain 2: _removable_2_1, _removable_2_2, ..., _removable_2_N
"""

import re
import random as _random_mod
from typing import Optional

REMOVABLE_PREFIX = "_removable_"

# List of (anchor_var, chain_idx) pairs — returned by augment_smt2.
ChainList = list[tuple[str, int]]


def _find_variables(smt2: str) -> list[str]:
    """Return all distinct xN variable names found in the formula."""
    return list(set(re.findall(r'\bx\d+\b', smt2)))


def augment_smt2(
    smt2: str,
    chain_length: int,
    max_count: int,
    rng: Optional[_random_mod.Random] = None,
) -> tuple[str, ChainList]:
    """
    Inject between 0 and max_count NOT chains into the formula.

    The actual count is sampled uniformly from [0, max_count]. Each chain is
    anchored to a distinct randomly chosen existing variable. Variables are
    named _ahint_{chain_idx}_{link_idx}.

    Returns:
        (augmented_formula, chains)
        chains = [(anchor_var, chain_idx), ...] — needed to compute hints later.
    """
    if rng is None:
        rng = _random_mod

    variables = _find_variables(smt2)
    if not variables:
        return smt2, []

    count = rng.randint(0, min(max_count, len(variables)))
    if count == 0:
        return smt2, []

    anchors = rng.sample(variables, count)
    chains: ChainList = []
    injections: list[str] = []

    for chain_idx, anchor in enumerate(anchors, start=1):
        def _var(i: int, ci: int = chain_idx) -> str:
            return f"{REMOVABLE_PREFIX}{ci}_{i}"

        declarations = "\n".join(
            f"(declare-fun {_var(i)} () Bool)" for i in range(1, chain_length + 1)
        )
        assertions = [f"(assert (= {_var(1)} (not {anchor})))"]
        for i in range(2, chain_length + 1):
            assertions.append(f"(assert (= {_var(i)} (not {_var(i - 1)})))")

        injections.append(
            f"\n; --- NOT chain {chain_idx}: {chain_length} links anchored to {anchor} ---\n"
            + declarations + "\n"
            + "\n".join(assertions) + "\n"
        )
        chains.append((anchor, chain_idx))

    augmented = smt2.replace("(check-sat)", "".join(injections) + "(check-sat)", 1)
    return augmented, chains
