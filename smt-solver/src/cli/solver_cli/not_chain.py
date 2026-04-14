"""
Linear chain augmentation for SMT-LIB formulas.

Injects one or more synthetic chains, each anchored to a distinct randomly
chosen declared variable, enlarging linear clusters in the compiled R1CS to
trigger P4 (Circom simplification threshold: 350 constraints).

For Boolean formulas each link is a NOT:
    y = not x

For finite-field formulas each link is the affine equivalent:
    y = 1 - x

Introduced variables use the `_removable_` prefix — the solver layer detects
this prefix in the sym/sr1cs file and eliminates all constraints involving
these wires before building the SMT query. Since the synthetic chain is fully
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
_DECLARE_FUN_RE = re.compile(
    r"^\s*\(declare-fun\s+([^\s()]+)\s+\(\)\s+(.+?)\)\s*$",
    re.MULTILINE,
)

# List of (anchor_var, chain_idx) pairs — returned by augment_smt2.
ChainList = list[tuple[str, int]]


def _find_declared_variables(smt2: str) -> list[tuple[str, str]]:
    """Return distinct declared zero-arity symbols together with their sorts."""
    seen: set[str] = set()
    variables: list[tuple[str, str]] = []
    for name, sort in _DECLARE_FUN_RE.findall(smt2):
        if name.startswith(REMOVABLE_PREFIX) or name in seen:
            continue
        seen.add(name)
        variables.append((name, sort.strip()))
    return variables


def _build_link_expression(source: str, sort: str) -> str:
    """Return the SMT-LIB expression for the next chain link."""
    if sort == "Bool":
        return f"(not {source})"
    return f"(ff.add (as ff1 {sort}) (ff.neg {source}))"


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

    variables = _find_declared_variables(smt2)
    if not variables:
        return smt2, []

    count = rng.randint(0, min(max_count, len(variables)))
    if count == 0:
        return smt2, []

    anchors = rng.sample(variables, count)
    chains: ChainList = []
    injections: list[str] = []

    for chain_idx, (anchor, sort) in enumerate(anchors, start=1):
        def _var(i: int, ci: int = chain_idx) -> str:
            return f"{REMOVABLE_PREFIX}{ci}_{i}"

        declarations = "\n".join(
            f"(declare-fun {_var(i)} () {sort})" for i in range(1, chain_length + 1)
        )
        assertions = [f"(assert (= {_var(1)} {_build_link_expression(anchor, sort)}))"]
        for i in range(2, chain_length + 1):
            assertions.append(
                f"(assert (= {_var(i)} {_build_link_expression(_var(i - 1), sort)}))"
            )

        injections.append(
            f"\n; --- NOT chain {chain_idx}: {chain_length} links anchored to {anchor} ---\n"
            + declarations + "\n"
            + "\n".join(assertions) + "\n"
        )
        chains.append((anchor, chain_idx))

    augmented = smt2.replace("(check-sat)", "".join(injections) + "(check-sat)", 1)
    return augmented, chains
