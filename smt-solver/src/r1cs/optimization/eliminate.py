"""
Wire elimination for R1CS.

Drops constraints that belong to the removable cone.
Used to remove _removable_ variables (e.g. NOT chain wires) from the SMT
query — they are fully determined by the circuit so their constraints are
always satisfied and add no information for the solver.
"""

from src.r1cs.ir import R1CS, Constraint


def eliminate_wires(
    r1cs: R1CS,
    removable_indices: set[int],
    protected_indices: set[int] | None = None,
) -> R1CS:
    """
    Drop the entire removable cone from the final SMT-facing R1CS.

    removable_indices are the named _removable_ seed wires. protected_indices
    are real problem wires (for this use case, original xN inputs) that must
    never become removable. We iteratively:
      1. remove any constraint touching a removable wire
      2. mark any unprotected helper wires from those removed constraints as
         removable too
    until a fixpoint is reached.
    """
    protected = set(protected_indices or set())
    removable = {
        idx for idx in removable_indices
        if idx not in protected and idx != 0
    }

    if not removable:
        return r1cs

    constraints = list(r1cs.constraints)
    while True:
        kept: list[Constraint] = []
        grew = False

        for constraint in constraints:
            used = set()
            for lc in (constraint.A, constraint.B, constraint.C):
                for term in lc.terms:
                    if term.variable.index != 0:  # skip constant wire
                        used.add(term.variable.index)

            if used.isdisjoint(removable):
                kept.append(constraint)
                continue

            new_removable = used - removable - protected
            if new_removable:
                removable.update(new_removable)
                grew = True

        constraints = kept
        if not grew:
            break

    kept_constraints = constraints

    kept_variables = [
        variable for variable in r1cs.variables
        if variable.index == 0 or variable.index not in removable
    ]
    kept_hints = {
        wire_idx: value for wire_idx, value in r1cs.hints.items()
        if wire_idx not in removable
    }

    kept_bool = r1cs.bool_wire_indices - removable
    kept_ternary = r1cs.ternary_wire_indices - removable

    surviving_indices = {variable.index for variable in kept_variables}
    kept_bool &= surviving_indices
    kept_ternary &= surviving_indices

    return R1CS(
        n8=r1cs.n8,
        prime=r1cs.prime,
        nVars=len(kept_variables),
        nOutputs=r1cs.nOutputs,
        nPubInputs=r1cs.nPubInputs,
        nPrvInputs=r1cs.nPrvInputs,
        nLabels=r1cs.nLabels,
        nConstraints=len(kept_constraints),
        useCustomGates=r1cs.useCustomGates,
        variables=kept_variables,
        constraints=kept_constraints,
        bool_wire_indices=kept_bool,
        ternary_wire_indices=kept_ternary,
        hints=kept_hints,
    )
