# Simplification Pipeline Findings

## Background

The Circom compiler's constraint simplification pipeline processes R1CS constraints in several stages:

1. **Equality simplification** — substitutes signals that are directly equal to another signal
2. **Constant equality simplification** — substitutes signals that are equal to a constant
3. **Linear simplification** — clusters linear constraints by shared signals and runs P3 or P4
4. **Non-linear simplification** — attempts to linearise quadratic constraints
5. **Iterative rounds** — repeats linear+nonlinear steps while new linear constraints emerge

Two compiler behaviours were investigated: which process (P3 vs P4) is selected for linear cluster simplification, and whether multiple iterative rounds are triggered.

---

## Finding 1: Chains of NOTs trigger P4

### Mechanism

Linear constraint clusters are built by union-find over constraints sharing signals. P4 is selected when a cluster has **≥ 350 constraints**. Boolean-only benchmarks (AND/OR/NOT of inputs) produce very small clusters — typically ≤ 10 constraints — because AND and OR gates compile to *quadratic* constraints, which are excluded from linear clustering entirely. Only NOT gates produce linear constraints (`out + in = 1`).

A chain of NOT gates — `c1 = NOT(c0)`, `c2 = NOT(c1)`, ..., `c_n = NOT(c_{n-1})` — generates one linear constraint per link, all sharing adjacent signals. This forms a single large connected cluster. Crucially, `c0` must be set to an **existing signal** from the benchmark (not a fresh one) so that the chain merges into an existing cluster rather than forming a new isolated cluster of its own.

### Experiment

`augment_clusters.py` injects a NOT chain of length ≥ 350 anchored to the most frequent variable in an existing benchmark. This reliably pushes the largest cluster past the P4 threshold. The current single-anchor approach is a starting point — the intended final strategy is to inject multiple shorter chains, each anchored to a different randomly chosen existing variable, distributing the augmentation more naturally across the constraint graph.

**Result:** cluster size 810 → P4 triggered. Without the chain, max cluster size was ≤ 17 → only P3.

### Key threshold (from `circom_algebra/src/simplification_utils.rs`)

```rust
let apply_less_occurrences = cluster_size >= 350 && cluster_size < 1_000_000 && !config.use_old_heuristics;
let process_name = if apply_less_occurrences { "process_4" } else { "process_3" };
```

---

## Finding 2: Cascade ORs with determined inputs trigger multiple rounds

### Mechanism

Multiple iterative rounds are triggered when non-linear (quadratic) constraints become linear after a round of substitution. The condition in `constraint_list/src/constraint_simplification.rs` is:

```rust
apply_round = !linear.is_empty() && no_rounds > 0
```

An OR gate compiles to `out = a + b - a*b` — quadratic. If one input is substituted to a known constant (0 or 1), the constraint becomes linear:
- `OR(0, b)` → `out = b` (linear)
- `OR(1, b)` → `out = 1` (constant)

A cascade of ORs — `OR(OR(OR(base, y1), y2), y3)...` — can propagate this collapse across rounds if each `y_i` is determined.

### Experiment

`gen_cascade_or.py` generates a deeply nested OR anchored to `AND(x1, NOT(x1))` (always false). The benchmark asserts `NOT(x1)` and `NOT(x2)`, forcing `x1=0`, `x2=0`. Making `y1..y5` intermediate signals defined as `y_i <== 1 - x1` (i.e. NOT of an input) ties their values organically to the same substitution.

After `x1 → 0`:
- `y1 = 1 - 0 = 1` (constant substitution)
- `OR(AND(0,1)=0, y1=1)` → `OR(0,1) = 1` (linearises in round 1)
- `OR(1, y2=1)` → `1` (linearises in round 2)
- ... and so on

**Result:** `cascade_or_003.circom` with `y_i <== 1 - x_i` produces **3 iterative rounds** instead of 1.

Contrast: with `y_i` as unconstrained intermediate signals (`<--` witness hint only), no value is determined for `y_i`, so OR stays quadratic — still 1 round.

---

## Summary

| Construct | Effect | Compiler path triggered |
|---|---|---|
| Chain of NOT gates (≥350) | Large linear cluster | **P4** selected over P3 |
| Cascade OR with determined inputs | Quadratic → linear across steps | **Multiple iterative rounds** |
| Boolean-only inputs (AND/OR of free signals) | Small clusters, no propagation | P3 only, 1 round |

The two constructs target orthogonal parts of the pipeline: NOT chains affect the *linear clustering phase*, while cascade ORs with known values affect the *iterative round condition* in non-linear simplification.

---

## TODO

- **Organic anchor for OR cascade**: For the NOT chain, anchoring `c0` to an existing variable merges the chain into an existing cluster — only connectivity matters. For the OR cascade, the anchor needs a *known value* (0 or 1) to trigger linearisation, which is a stronger requirement. Using `x1` as the base (instead of `AND(x1, NOT(x1))`) would be more organic but only works if `x1=0` is already forced by existing constraints, making it benchmark-specific. The `AND(x1, NOT(x1))` base is self-contained and benchmark-agnostic, but artificial. Investigate whether there is a principled way to anchor the OR cascade to existing signals generically.
