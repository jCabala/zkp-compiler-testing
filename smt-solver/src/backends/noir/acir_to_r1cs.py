from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.r1cs.ir import Constraint, LinearCombination, R1CS, Term, Variable
from src.r1cs.sr1cs import dump_sr1cs


BN254_FR_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617
_WITNESS_RE = re.compile(r"^w([0-9]+)$")
_TOKEN_RE = re.compile(r"\s*(w[0-9]+|[0-9]+|==|!=|[=()+\-*])")


@dataclass
class NoirR1CSTranslation:
    r1cs: R1CS
    input_wires: list[int]
    output_wires: list[int]
    witness_map: dict[str, int]


class _Expr:
    pass


@dataclass
class _Const(_Expr):
    value: int


@dataclass
class _Wire(_Expr):
    name: str


@dataclass
class _Neg(_Expr):
    value: _Expr


@dataclass
class _BinOp(_Expr):
    op: str
    lhs: _Expr
    rhs: _Expr


class _Poly:
    def __init__(self, prime: int, terms: dict[tuple[int, ...], int] | None = None):
        self.prime = prime
        self.terms: dict[tuple[int, ...], int] = {}
        if terms:
            for monomial, coeff in terms.items():
                self._add_term(monomial, coeff)

    @classmethod
    def constant(cls, value: int, prime: int) -> "_Poly":
        return cls(prime, {(): value})

    @classmethod
    def wire(cls, wire_idx: int, prime: int) -> "_Poly":
        return cls(prime, {(wire_idx,): 1})

    def copy(self) -> "_Poly":
        return _Poly(self.prime, dict(self.terms))

    def __add__(self, other: "_Poly") -> "_Poly":
        out = self.copy()
        for monomial, coeff in other.terms.items():
            out._add_term(monomial, coeff)
        return out

    def __sub__(self, other: "_Poly") -> "_Poly":
        out = self.copy()
        for monomial, coeff in other.terms.items():
            out._add_term(monomial, -coeff)
        return out

    def __neg__(self) -> "_Poly":
        return _Poly(self.prime, {monomial: (-coeff) % self.prime for monomial, coeff in self.terms.items()})

    def __mul__(self, other: "_Poly") -> "_Poly":
        out = _Poly(self.prime)
        for monomial_a, coeff_a in self.terms.items():
            for monomial_b, coeff_b in other.terms.items():
                merged = tuple(sorted(monomial_a + monomial_b))
                if len(merged) > 2:
                    raise ValueError("ACIR assertion exceeds quadratic degree; cannot translate to R1CS")
                out._add_term(merged, coeff_a * coeff_b)
        return out

    def is_zero(self) -> bool:
        return not self.terms

    def constant_term(self) -> int:
        return self.terms.get((), 0)

    def linear_terms(self) -> dict[int, int]:
        return {monomial[0]: coeff for monomial, coeff in self.terms.items() if len(monomial) == 1}

    def quadratic_terms(self) -> dict[tuple[int, int], int]:
        return {monomial: coeff for monomial, coeff in self.terms.items() if len(monomial) == 2}

    def without_quadratic_terms(self) -> "_Poly":
        return _Poly(self.prime, {monomial: coeff for monomial, coeff in self.terms.items() if len(monomial) < 2})

    def _add_term(self, monomial: tuple[int, ...], coeff: int):
        reduced = coeff % self.prime
        if reduced == 0:
            return
        new_coeff = (self.terms.get(monomial, 0) + reduced) % self.prime
        if new_coeff == 0:
            self.terms.pop(monomial, None)
        else:
            self.terms[monomial] = new_coeff


class _TokenStream:
    def __init__(self, text: str):
        self.tokens = [match.group(1) for match in _TOKEN_RE.finditer(text)]
        compact = "".join(self.tokens)
        if compact != re.sub(r"\s+", "", text):
            raise ValueError(f"Unsupported ASSERT expression syntax: {text}")
        self.index = 0

    def peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self) -> str:
        token = self.peek()
        if token is None:
            raise ValueError("Unexpected end of ASSERT expression")
        self.index += 1
        return token


def translate_decoded_noir_acir_to_r1cs(decoded_path: Path, output_path: Path | None = None) -> Path:
    decoded = json.loads(decoded_path.read_text())
    translation = build_r1cs_from_decoded_noir_acir(decoded)
    sr1cs_text = dump_sr1cs(
        translation.r1cs,
        input_wires=translation.input_wires,
        output_wires=translation.output_wires,
    )
    if output_path is None:
        output_path = decoded_path.with_name(decoded_path.name.replace(".json.decoded.json", ".sr1cs"))
        if output_path == decoded_path:
            output_path = decoded_path.with_suffix(".sr1cs")
    output_path.write_text(sr1cs_text)
    return output_path


def build_r1cs_from_decoded_noir_acir(decoded: dict) -> NoirR1CSTranslation:
    function = _main_function(decoded)
    assert_texts = _main_asserts(function)
    prime = BN254_FR_PRIME

    referenced_witnesses: set[int] = set()
    for witness_name in function.get("private_parameters", []):
        referenced_witnesses.add(_parse_witness_name(witness_name))
    for witness_name in function.get("public_parameters", []):
        referenced_witnesses.add(_parse_witness_name(witness_name))
    for witness_name in function.get("return_values", []):
        referenced_witnesses.add(_parse_witness_name(witness_name))
    for assert_text in assert_texts:
        referenced_witnesses.update(_referenced_witnesses_in_assert(assert_text))

    witness_map = {f"w{witness_idx}": witness_idx + 1 for witness_idx in sorted(referenced_witnesses)}
    next_wire_idx = (max(witness_map.values()) + 1) if witness_map else 1

    constraints: list[Constraint] = []
    for assert_text in assert_texts:
        polynomial = _assert_text_to_polynomial(assert_text, witness_map=witness_map, prime=prime)
        rows, next_wire_idx = _polynomial_to_r1cs_constraints(polynomial, next_wire_idx=next_wire_idx, prime=prime)
        constraints.extend(rows)

    nvars = max((next_wire_idx, *(wire + 1 for wire in witness_map.values())), default=1)
    variables = [Variable(i) for i in range(nvars)]
    input_wires = [_parse_witness_name(name) + 1 for name in function.get("private_parameters", []) + function.get("public_parameters", [])]
    output_wires = [_parse_witness_name(name) + 1 for name in function.get("return_values", [])]

    r1cs = R1CS(
        n8=0,
        prime=prime,
        nVars=nvars,
        nOutputs=len(output_wires),
        nPubInputs=len(function.get("public_parameters", [])),
        nPrvInputs=len(function.get("private_parameters", [])),
        nLabels=nvars,
        nConstraints=len(constraints),
        useCustomGates=False,
        variables=variables,
        constraints=constraints,
    )
    return NoirR1CSTranslation(
        r1cs=r1cs,
        input_wires=input_wires,
        output_wires=output_wires,
        witness_map=witness_map,
    )


def _main_function(decoded: dict) -> dict:
    functions = decoded.get("inspector_output", {}).get("functions", [])
    if not functions:
        raise ValueError("Decoded ACIR JSON does not contain any functions")
    return functions[0]


def _main_asserts(function: dict) -> list[str]:
    assert_texts: list[str] = []
    seen_helper = False
    for opcode in function.get("opcodes", []):
        kind = opcode.get("kind")
        text = opcode.get("text", "")
        if kind == "unconstrained":
            seen_helper = True
            continue
        if seen_helper:
            continue
        if kind == "ASSERT":
            assert_texts.append(text)
            continue
        if kind == "BRILLIG":
            continue
        raise ValueError(f"Unsupported ACIR opcode in main function: {text}")
    return assert_texts


def _parse_witness_name(name: str) -> int:
    match = _WITNESS_RE.fullmatch(name.strip())
    if match is None:
        raise ValueError(f"Unsupported witness name: {name}")
    return int(match.group(1))


def _referenced_witnesses_in_assert(assert_text: str) -> set[int]:
    return {int(match.group(1)) for match in re.finditer(r"\bw([0-9]+)\b", assert_text)}


def _assert_text_to_polynomial(assert_text: str, *, witness_map: dict[str, int], prime: int) -> _Poly:
    if not assert_text.startswith("ASSERT "):
        raise ValueError(f"Unsupported opcode text: {assert_text}")
    body = assert_text[len("ASSERT "):]
    lhs_text, rhs_text = [part.strip() for part in body.split("=", 1)]
    lhs = _expr_to_poly(_parse_expr(lhs_text), witness_map=witness_map, prime=prime)
    rhs = _expr_to_poly(_parse_expr(rhs_text), witness_map=witness_map, prime=prime)
    return lhs - rhs


def _parse_expr(text: str) -> _Expr:
    stream = _TokenStream(text)

    def parse_sum() -> _Expr:
        node = parse_product()
        while stream.peek() in {"+", "-"}:
            op = stream.pop()
            rhs = parse_product()
            node = _BinOp(op, node, rhs)
        return node

    def parse_product() -> _Expr:
        node = parse_unary()
        while stream.peek() == "*":
            stream.pop()
            rhs = parse_unary()
            node = _BinOp("*", node, rhs)
        return node

    def parse_unary() -> _Expr:
        token = stream.peek()
        if token == "-":
            stream.pop()
            return _Neg(parse_unary())
        if token == "(":
            stream.pop()
            node = parse_sum()
            if stream.pop() != ")":
                raise ValueError(f"Unbalanced ASSERT expression: {text}")
            return node
        if token is None:
            raise ValueError(f"Unexpected end of ASSERT expression: {text}")
        stream.pop()
        if token.startswith("w"):
            return _Wire(token)
        return _Const(int(token))

    expr = parse_sum()
    if stream.peek() is not None:
        raise ValueError(f"Unexpected trailing token {stream.peek()} in ASSERT expression: {text}")
    return expr


def _expr_to_poly(expr: _Expr, *, witness_map: dict[str, int], prime: int) -> _Poly:
    if isinstance(expr, _Const):
        return _Poly.constant(expr.value, prime)
    if isinstance(expr, _Wire):
        if expr.name not in witness_map:
            raise ValueError(f"Missing witness mapping for {expr.name}")
        return _Poly.wire(witness_map[expr.name], prime)
    if isinstance(expr, _Neg):
        return -_expr_to_poly(expr.value, witness_map=witness_map, prime=prime)
    if isinstance(expr, _BinOp):
        lhs = _expr_to_poly(expr.lhs, witness_map=witness_map, prime=prime)
        rhs = _expr_to_poly(expr.rhs, witness_map=witness_map, prime=prime)
        if expr.op == "+":
            return lhs + rhs
        if expr.op == "-":
            return lhs - rhs
        if expr.op == "*":
            return lhs * rhs
    raise TypeError(f"Unsupported expression node: {expr!r}")


def _polynomial_to_r1cs_constraints(polynomial: _Poly, *, next_wire_idx: int, prime: int) -> tuple[list[Constraint], int]:
    if polynomial.is_zero():
        return [], next_wire_idx

    quadratic_terms = sorted(polynomial.quadratic_terms().items())
    constraints: list[Constraint] = []

    if len(quadratic_terms) <= 1:
        constraint = _single_polynomial_constraint(polynomial, prime=prime)
        return ([constraint] if constraint is not None else []), next_wire_idx

    affine_poly = polynomial.without_quadratic_terms()
    for (lhs_wire, rhs_wire), coeff in quadratic_terms:
        temp_wire = next_wire_idx
        next_wire_idx += 1
        constraints.append(
            Constraint(
                A=LinearCombination([Term(variable=Variable(lhs_wire), coeff=coeff)]),
                B=LinearCombination([Term(variable=Variable(rhs_wire), coeff=1)]),
                C=LinearCombination([Term(variable=Variable(temp_wire), coeff=1)]),
            )
        )
        affine_poly = affine_poly + _Poly(prime, {(temp_wire,): 1})

    final_constraint = _single_polynomial_constraint(affine_poly, prime=prime)
    if final_constraint is not None:
        constraints.append(final_constraint)
    return constraints, next_wire_idx


def _single_polynomial_constraint(polynomial: _Poly, *, prime: int) -> Constraint | None:
    if polynomial.is_zero():
        return None

    quadratic_terms = list(polynomial.quadratic_terms().items())
    if len(quadratic_terms) > 1:
        raise ValueError("Expected at most one quadratic term after splitting")

    if quadratic_terms:
        (lhs_wire, rhs_wire), coeff = quadratic_terms[0]
        linear_tail = polynomial.without_quadratic_terms()
        return Constraint(
            A=LinearCombination([Term(variable=Variable(lhs_wire), coeff=coeff)]),
            B=LinearCombination([Term(variable=Variable(rhs_wire), coeff=1)]),
            C=_linear_combination_from_poly(-linear_tail),
        )

    return Constraint(
        A=_linear_combination_from_poly(polynomial),
        B=LinearCombination([Term(variable=Variable(0), coeff=1)]),
        C=LinearCombination([]),
    )


def _linear_combination_from_poly(polynomial: _Poly) -> LinearCombination:
    terms: list[Term] = []
    constant = polynomial.constant_term()
    if constant != 0:
        terms.append(Term(variable=Variable(0), coeff=constant))
    for wire_idx, coeff in sorted(polynomial.linear_terms().items()):
        if coeff != 0:
            terms.append(Term(variable=Variable(wire_idx), coeff=coeff))
    return LinearCombination(terms)
