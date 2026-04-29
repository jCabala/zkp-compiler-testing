import random
from math import gcd
from pathlib import Path

# BN254 scalar field — the prime used by Circom (non-negotiable)
CIRCOM_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def _sample_alpha(rng: random.Random) -> int:
    candidates = list(range(3, 20))
    rng.shuffle(candidates)
    for alpha in candidates:
        if gcd(alpha, CIRCOM_PRIME - 1) == 1:
            return alpha
    raise ValueError("No valid S-box exponent found for the Circom prime")


def _det_mod_p(M: list[list[int]], p: int) -> int:
    """Determinant of a square matrix over F_p via Gaussian elimination."""
    n = len(M)
    A = [row[:] for row in M]
    det = 1
    for col in range(n):
        pivot = next((row for row in range(col, n) if A[row][col] % p != 0), None)
        if pivot is None:
            return 0
        if pivot != col:
            A[col], A[pivot] = A[pivot], A[col]
            det = (-det) % p
        det = (det * A[col][col]) % p
        inv = pow(A[col][col], p - 2, p)
        for row in range(col + 1, n):
            factor = (A[row][col] * inv) % p
            for k in range(col, n):
                A[row][k] = (A[row][k] - factor * A[col][k]) % p
    return det % p


def _sample_mds(rng: random.Random, t: int) -> list[list[int]]:
    p = CIRCOM_PRIME
    for _ in range(1000):
        M = [[rng.randint(0, p - 1) for _ in range(t)] for _ in range(t)]
        if _det_mod_p(M, p) != 0:
            return M
    raise ValueError(f"Could not sample invertible {t}x{t} matrix mod CIRCOM_PRIME")


def _sample_sparse_mds(rng: random.Random, t: int) -> list[list[int]]:
    """Sample a sparse invertible matrix.

    We use an upper-triangular matrix with ones on the diagonal and a small
    number of non-zero off-diagonal entries. This preserves bijectivity while
    producing much simpler benchmark terms than a dense random matrix.
    """
    p = CIRCOM_PRIME
    M = [[0] * t for _ in range(t)]
    for i in range(t):
        M[i][i] = 1
    for i in range(t - 1):
        M[i][i + 1] = rng.randint(1, p - 1)
    return M


def _sample_identity_mds(t: int) -> list[list[int]]:
    return [[1 if i == j else 0 for j in range(t)] for i in range(t)]


def _sample_linear_layer(rng: random.Random, t: int, mds_mode: str) -> list[list[int]]:
    if mds_mode == "random":
        return _sample_mds(rng, t)
    if mds_mode == "sparse":
        return _sample_sparse_mds(rng, t)
    if mds_mode == "identity":
        return _sample_identity_mds(t)
    raise ValueError(f"Unsupported mds_mode: {mds_mode}")


def _poseidon_permute(
    state: list[int],
    M: list[list[int]],
    round_consts: list[list[int]],
    alpha: int,
) -> list[int]:
    p = CIRCOM_PRIME
    t = len(state)
    s = state[:]
    for r in range(len(round_consts)):
        s = [(s[i] + round_consts[r][i]) % p for i in range(t)]
        s = [pow(x, alpha, p) for x in s]
        s = [sum(M[i][j] * s[j] for j in range(t)) % p for i in range(t)]
    return s


def _ff_lit(n: int) -> str:
    return f"(as ff{n % CIRCOM_PRIME} F)"


def _ff_pow(var: str, alpha: int) -> str:
    """Encode var^alpha as nested ff.mul calls."""
    result = var
    for _ in range(alpha - 1):
        result = f"(ff.mul {result} {var})"
    return result


def _generate_smt2(
    t: int,
    alpha: int,
    M: list[list[int]],
    round_consts: list[list[int]],
    output: list[int],
) -> str:
    rounds = len(round_consts)
    lines = [
        f"; Poseidon-like permutation benchmark (unique SAT)",
        f"; prime=CIRCOM (BN254)  t={t}  alpha={alpha}  rounds={rounds}",
        f"(set-logic QF_FF)",
        f"",
        f"(define-sort F () (_ FiniteField {CIRCOM_PRIME}))",
        f"",
    ]

    for i in range(t):
        lines.append(f"(declare-fun x{i} () F)")
    lines.append("")

    # Build nested let-binding layers (one per step per round).
    # This avoids both declare-fun for intermediates and exponential expression blowup.
    let_layers: list[list[tuple[str, str]]] = []
    state = [f"x{i}" for i in range(t)]

    for r in range(rounds):
        arc_names = [f"arc_r{r}_s{i}" for i in range(t)]
        let_layers.append([
            (arc_names[i], f"(ff.add {state[i]} {_ff_lit(round_consts[r][i])})")
            for i in range(t)
        ])

        sb_names = [f"sb_r{r}_s{i}" for i in range(t)]
        let_layers.append([
            (sb_names[i], _ff_pow(arc_names[i], alpha))
            for i in range(t)
        ])

        mds_names = [f"mds_r{r}_s{i}" for i in range(t)]
        let_layers.append([
            (mds_names[i], "(ff.add " + " ".join(
                f"(ff.mul {_ff_lit(M[i][j])} {sb_names[j]})" for j in range(t)
            ) + ")")
            for i in range(t)
        ])

        state = mds_names

    # Innermost body: assert all output elements equal known values
    body = "(and " + " ".join(f"(= {state[i]} {_ff_lit(output[i])})" for i in range(t)) + ")"

    # Wrap with let layers from innermost to outermost
    for layer in reversed(let_layers):
        bindings = " ".join(f"({name} {expr})" for name, expr in layer)
        body = f"(let ({bindings})\n{body})"

    lines.append("; Output fixed to precomputed value — unique solution exists by bijectivity")
    lines.append(f"(assert {body})")
    lines.append("")
    lines.append("(check-sat)")

    return "\n".join(lines) + "\n"


def generate_poseidon_benchmarks(
    out_folder: Path,
    count: int = 10,
    seed=None,
    min_rounds: int = 1,
    max_rounds: int = 5,
    state_width: int | None = None,
    mds_mode: str = "random",
    log=print,
) -> None:
    p = CIRCOM_PRIME
    rng = random.Random(seed)
    out_folder.mkdir(parents=True, exist_ok=True)

    if state_width is not None and state_width <= 0:
        raise ValueError("state_width must be positive")

    generated = 0
    attempts = 0

    while generated < count and attempts < count * 50:
        attempts += 1
        try:
            t = state_width if state_width is not None else rng.choice([2, 3])
            alpha = 5
            rounds = rng.randint(min_rounds, max_rounds)
            M = _sample_linear_layer(rng, t, mds_mode)
            round_consts = [[rng.randint(0, p - 1) for _ in range(t)] for _ in range(rounds)]
            x = [rng.randint(0, p - 1) for _ in range(t)]
            y = _poseidon_permute(x, M, round_consts, alpha)

            smt2 = _generate_smt2(t, alpha, M, round_consts, y)
            out_file = out_folder / f"poseidon_{generated + 1:04d}.smt2"
            out_file.write_text(smt2)
            generated += 1
            log(f"  [{generated}/{count}] {out_file.name}  t={t} alpha={alpha} rounds={rounds}")
        except ValueError as e:
            log(f"  Skipping attempt {attempts}: {e}")

    if generated < count:
        log(f"Warning: generated only {generated}/{count} benchmarks after {attempts} attempts")
    else:
        log(f"Done: {generated} benchmarks written to {out_folder}")
