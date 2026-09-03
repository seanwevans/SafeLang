"""Adversarial falsification of SafeLang domain contracts.

The SafeLang philosophy is that the compiler is the program's adversary: it
tries to *falsify* the program rather than to confirm it.  This module is the
part of the toolchain that actually does that, using the Z3 SMT solver.

For each function it symbolically executes the body, treating the ``consume``
domains as assumptions and every ``emit`` domain as a proof obligation.  It
then asks Z3 for a witness that breaks the obligation.  If Z3 finds one, the
program is falsified and the counterexample is reported.  If Z3 proves no such
witness exists, the obligation has survived.

What is modelled, and what is not, is deliberately explicit:

* All values are modelled as mathematical reals.  Floating-point rounding and
  integer saturation are *not* modelled, so a result proven in-domain here is
  proven for exact arithmetic.
* Only the statement forms below are understood.  Anything else makes the
  function ``inconclusive`` rather than verified -- the pass never claims a
  proof over a body it did not fully read.

Supported statements::

    name = expr                 assignment
    cond ? name = expr          guarded assignment
    return expr                 bound to the single emit variable, if there is one

Z3 is an optional dependency; install it with ``pip install safelang[verify]``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

from .parser import (
    _DOMAIN_RE,
    _PARAM_RE,
    _sanitize,
    _split_contract_entry,
    FunctionDef,
)

try:  # pragma: no cover - exercised by the import-guard test
    import z3
except ImportError:  # pragma: no cover - depends on the environment
    z3 = None


VERIFIED = "verified"
FALSIFIED = "falsified"
INCONCLUSIVE = "inconclusive"

# Rational stand-ins for the symbolic constants the domain syntax allows.  The
# same values are used in domains and in expressions so the two always agree.
_NAMED_CONSTANTS = {
    "pi": Fraction(math.pi),
    "e": Fraction(math.e),
}


class FalsificationUnavailable(RuntimeError):
    """Raised when the falsifier is asked to run without Z3 installed."""


class _Unsupported(Exception):
    """Internal signal that a construct is outside the modelled subset."""


def z3_available() -> bool:
    """Return ``True`` when the Z3 backend can be used."""

    return z3 is not None


# ---------------------------------------------------------------------------
# domains
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    """A closed/open interval over the reals, with optional infinite ends."""

    lower: Optional[Fraction]
    upper: Optional[Fraction]
    lower_closed: bool
    upper_closed: bool
    text: str

    def constrain(self, term):
        """Return the Z3 predicate asserting ``term`` lies in this interval."""

        parts = []
        if self.lower is not None:
            bound = z3.RealVal(self.lower)
            parts.append(term >= bound if self.lower_closed else term > bound)
        if self.upper is not None:
            bound = z3.RealVal(self.upper)
            parts.append(term <= bound if self.upper_closed else term < bound)
        if not parts:
            return z3.BoolVal(True)
        return z3.And(*parts) if len(parts) > 1 else parts[0]


def _parse_domain_value(token: str) -> Optional[Fraction]:
    """Convert one domain endpoint into a rational, or ``None`` for infinity.

    Raises ``_Unsupported`` for identifiers the falsifier cannot resolve.
    """

    text = token.strip().replace("_", "")
    sign = 1
    if text[:1] in {"+", "-"}:
        if text[0] == "-":
            sign = -1
        text = text[1:]

    lowered = text.lower()
    if lowered == "inf":
        return None
    if lowered in _NAMED_CONSTANTS:
        return sign * _NAMED_CONSTANTS[lowered]
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return sign * Fraction(int(numerator), int(denominator))
    try:
        return sign * Fraction(text)
    except ValueError as exc:
        raise _Unsupported(f"unresolved domain endpoint {token!r}") from exc


def parse_interval(domain_expr: str) -> Interval:
    """Parse a ``# [a, b]`` domain fragment into an :class:`Interval`."""

    match = _DOMAIN_RE.fullmatch(domain_expr)
    if not match:
        raise _Unsupported(f"unparsable domain {domain_expr.strip()!r}")

    open_bracket, low_token, high_token, close_bracket = match.groups()
    lower = _parse_domain_value(low_token)
    upper = _parse_domain_value(high_token)
    return Interval(
        lower=lower,
        upper=upper,
        lower_closed=open_bracket == "[",
        upper_closed=close_bracket == "]",
        text=domain_expr.strip(),
    )


def _contract_entries(entries: Sequence[str]) -> List[Tuple[str, str, str]]:
    """Return ``(type, name, domain)`` triples for a contract block."""

    parsed: List[Tuple[str, str, str]] = []
    for entry in entries:
        signature, domain_expr = _split_contract_entry(entry)
        if signature == "nil":
            continue
        match = _PARAM_RE.fullmatch(signature)
        if not match or domain_expr is None:
            raise _Unsupported(f"malformed contract entry {entry.strip()!r}")
        parsed.append((match.group(1), match.group(2), domain_expr))
    return parsed


# ---------------------------------------------------------------------------
# expressions
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
      (?P<number>\d+(?:_\d+)*(?:\.\d+(?:_\d+)*)?|\.\d+(?:_\d+)*)
    | (?P<name>[A-Za-z_]\w*)
    | (?P<op><=|>=|==|[-+*/()<>])
    | (?P<space>\s+)
    """,
    re.VERBOSE,
)

_COMPARISONS = {"<", "<=", ">", ">=", "=="}


def _tokenize(expr: str) -> List[str]:
    tokens: List[str] = []
    pos = 0
    while pos < len(expr):
        match = _TOKEN_RE.match(expr, pos)
        if not match:
            raise _Unsupported(
                f"unexpected character {expr[pos]!r} in {expr.strip()!r}"
            )
        pos = match.end()
        if match.lastgroup == "space":
            continue
        tokens.append(match.group())
    return tokens


class _ExprParser:
    """Recursive-descent parser producing Z3 terms from SafeLang expressions."""

    def __init__(self, tokens: List[str], lookup):
        self._tokens = tokens
        self._pos = 0
        self._lookup = lookup
        self.divisors: List[object] = []

    # -- token helpers ----------------------------------------------------
    def _peek(self) -> Optional[str]:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _take(self) -> str:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _accept(self, *candidates: str) -> Optional[str]:
        if self._peek() in candidates:
            return self._take()
        return None

    # -- grammar ----------------------------------------------------------
    def parse(self):
        value = self._or_expr()
        if self._peek() is not None:
            raise _Unsupported(f"trailing token {self._peek()!r}")
        return value

    def _or_expr(self):
        value = self._and_expr()
        while self._accept("or"):
            value = z3.Or(value, self._and_expr())
        return value

    def _and_expr(self):
        value = self._cmp_expr()
        while self._accept("and"):
            value = z3.And(value, self._cmp_expr())
        return value

    def _cmp_expr(self):
        left = self._add_expr()
        operator = self._peek()
        if operator in _COMPARISONS:
            self._take()
            right = self._add_expr()
            if operator == "<":
                return left < right
            if operator == "<=":
                return left <= right
            if operator == ">":
                return left > right
            if operator == ">=":
                return left >= right
            return left == right
        return left

    def _add_expr(self):
        value = self._mul_expr()
        while True:
            operator = self._accept("+", "-")
            if operator is None:
                return value
            right = self._mul_expr()
            value = value + right if operator == "+" else value - right

    def _mul_expr(self):
        value = self._unary()
        while True:
            operator = self._accept("*", "/")
            if operator is None:
                return value
            right = self._unary()
            if operator == "*":
                value = value * right
            else:
                self.divisors.append(right)
                value = value / right

    def _unary(self):
        if self._accept("-"):
            return -self._unary()
        if self._accept("+"):
            return self._unary()
        if self._accept("not"):
            return z3.Not(self._unary())
        return self._primary()

    def _primary(self):
        token = self._peek()
        if token is None:
            raise _Unsupported("unexpected end of expression")
        if token == "(":
            self._take()
            value = self._or_expr()
            if self._accept(")") is None:
                raise _Unsupported("unbalanced parentheses")
            return value
        self._take()
        if token[0].isdigit() or token[0] == ".":
            return z3.RealVal(Fraction(token.replace("_", "")))
        lowered = token.lower()
        if lowered in _NAMED_CONSTANTS:
            return z3.RealVal(_NAMED_CONSTANTS[lowered])
        if lowered == "inf":
            raise _Unsupported("'inf' is not a value the solver can reason about")
        if lowered in {"true", "false"}:
            return z3.BoolVal(lowered == "true")
        return self._lookup(token)


# ---------------------------------------------------------------------------
# symbolic execution
# ---------------------------------------------------------------------------

_ASSIGN_RE = re.compile(r"^(?P<target>[^=<>!?]+?)=(?!=)(?P<value>.+)$")


def _statements(fn: FunctionDef) -> List[str]:
    """Return the executable statement lines of ``fn``, comments removed."""

    lines: List[str] = []
    in_block = False
    for raw in _sanitize(fn.body).splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if in_block:
            if stripped.endswith("}"):
                in_block = False
            continue
        if stripped.startswith("@"):
            continue
        if stripped.startswith("consume") or stripped.startswith("emit"):
            if not stripped.endswith("}"):
                in_block = True
            continue
        lines.append(stripped.rstrip(";"))
    return lines


@dataclass
class Counterexample:
    """One way the adversary broke the program."""

    kind: str
    variable: str
    detail: str
    witness: Dict[str, str] = field(default_factory=dict)

    def describe(self) -> str:
        text = f"{self.variable}: {self.detail}"
        if self.witness:
            bindings = ", ".join(f"{k}={v}" for k, v in sorted(self.witness.items()))
            text += f" [witness: {bindings}]"
        return text


@dataclass
class FunctionReport:
    """The verdict for a single function."""

    name: str
    status: str
    counterexamples: List[Counterexample] = field(default_factory=list)
    unsupported: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == VERIFIED


class _Machine:
    """Tracks the symbolic value and definedness of every variable."""

    def __init__(self):
        self.terms: Dict[str, object] = {}
        self.defined: Dict[str, object] = {}
        self.division_guards: List[Tuple[str, object, object]] = []
        self._fresh = 0

    def declare(self, name: str, defined: bool) -> None:
        self.terms[name] = z3.Real(name)
        self.defined[name] = z3.BoolVal(defined)

    def lookup(self, name: str):
        if name not in self.terms:
            # An unassigned read: give it a fresh unconstrained value and
            # remember that it is not yet defined.
            self._fresh += 1
            self.terms[name] = z3.Real(f"{name}!undef{self._fresh}")
            self.defined[name] = z3.BoolVal(False)
        return self.terms[name]

    def assign(self, name: str, value, guard=None) -> None:
        if guard is None:
            self.terms[name] = value
            self.defined[name] = z3.BoolVal(True)
            return
        previous = self.lookup(name)
        was_defined = self.defined[name]
        self.terms[name] = z3.If(guard, value, previous)
        self.defined[name] = z3.Or(guard, was_defined)

    def parse(self, expr: str, statement: str, guard=None):
        parser = _ExprParser(_tokenize(expr), self.lookup)
        value = parser.parse()
        reached = z3.BoolVal(True) if guard is None else guard
        for divisor in parser.divisors:
            self.division_guards.append((statement, divisor, reached))
        return value


def _split_guard(statement: str) -> Tuple[Optional[str], str]:
    if "?" not in statement:
        return None, statement
    condition, _, action = statement.partition("?")
    return condition.strip(), action.strip()


def _execute(fn: FunctionDef, machine: _Machine, emit_names: List[str]) -> List[str]:
    """Run the body through ``machine``; return statements it could not model."""

    unsupported: List[str] = []
    for statement in _statements(fn):
        try:
            condition_text, action = _split_guard(statement)
            guard = (
                machine.parse(condition_text, statement)
                if condition_text is not None
                else None
            )
            if guard is not None and not z3.is_bool(guard):
                raise _Unsupported("guard is not a condition")

            if action.startswith("return"):
                if len(emit_names) != 1:
                    raise _Unsupported(
                        "'return' needs exactly one emit variable to bind to"
                    )
                target, value_text = emit_names[0], action[len("return") :]
            else:
                match = _ASSIGN_RE.match(action)
                if not match:
                    raise _Unsupported("not an assignment")
                target = match.group("target").strip()
                value_text = match.group("value")
                if not re.fullmatch(r"[A-Za-z_]\w*", target):
                    raise _Unsupported(f"unsupported assignment target {target!r}")

            value = machine.parse(value_text, statement, guard)
            if z3.is_bool(value):
                raise _Unsupported("assigned value is a condition, not a number")
            machine.assign(target, value, guard)
        except _Unsupported as exc:
            unsupported.append(f"{statement}  ({exc})")
    return unsupported


def _witness(model, machine: _Machine, names: Sequence[str]) -> Dict[str, str]:
    """Render the solver's model for the named inputs."""

    bindings: Dict[str, str] = {}
    for name in names:
        term = machine.terms.get(name)
        if term is None:
            continue
        value = model.eval(term, model_completion=True)
        try:
            number = float(value.as_fraction())
        except AttributeError:  # pragma: no cover - non-numeral model value
            bindings[name] = str(value)
            continue
        bindings[name] = f"{number:g}"
    return bindings


def falsify_function(fn: FunctionDef) -> FunctionReport:
    """Try to falsify a single function's ``emit`` domain obligations."""

    if z3 is None:  # pragma: no cover - guarded by the caller
        raise FalsificationUnavailable("z3-solver is not installed")

    report = FunctionReport(name=fn.name, status=VERIFIED)

    try:
        consume_entries = _contract_entries(fn.consume)
        emit_entries = _contract_entries(fn.emit)
    except _Unsupported as exc:
        report.status = INCONCLUSIVE
        report.notes.append(str(exc))
        return report

    machine = _Machine()
    assumptions = []
    input_names = []
    for _type, name, domain_expr in consume_entries:
        machine.declare(name, defined=True)
        input_names.append(name)
        try:
            assumptions.append(
                parse_interval(domain_expr).constrain(machine.terms[name])
            )
        except _Unsupported as exc:
            report.status = INCONCLUSIVE
            report.notes.append(f"consume {name}: {exc}")
            return report

    emit_names = [name for _type, name, _domain in emit_entries]
    report.unsupported = _execute(fn, machine, emit_names)

    if not emit_entries:
        report.notes.append("no emit domain obligations to falsify")
        return report

    if report.unsupported:
        # Skipping a statement means we may have skipped the very assignment
        # that would satisfy an obligation, so no verdict is trustworthy here.
        report.status = INCONCLUSIVE
        return report

    solver = z3.Solver()
    for assumption in assumptions:
        solver.add(assumption)

    for statement, divisor, reached in machine.division_guards:
        solver.push()
        solver.add(reached)
        solver.add(divisor == 0)
        if solver.check() == z3.sat:
            report.counterexamples.append(
                Counterexample(
                    kind="division-by-zero",
                    variable=statement,
                    detail="divisor can be zero",
                    witness=_witness(solver.model(), machine, input_names),
                )
            )
        solver.pop()

    for _type, name, domain_expr in emit_entries:
        try:
            interval = parse_interval(domain_expr)
        except _Unsupported as exc:
            report.status = INCONCLUSIVE
            report.notes.append(f"emit {name}: {exc}")
            return report

        if name not in machine.terms:
            report.counterexamples.append(
                Counterexample(
                    kind="unassigned",
                    variable=name,
                    detail="never assigned in the body",
                )
            )
            continue

        solver.push()
        solver.add(z3.Not(machine.defined[name]))
        if solver.check() == z3.sat:
            report.counterexamples.append(
                Counterexample(
                    kind="unassigned",
                    variable=name,
                    detail="can leave the body unassigned",
                    witness=_witness(solver.model(), machine, input_names),
                )
            )
        solver.pop()

        solver.push()
        solver.add(machine.defined[name])
        solver.add(z3.Not(interval.constrain(machine.terms[name])))
        if solver.check() == z3.sat:
            model = solver.model()
            witness = _witness(model, machine, input_names)
            witness[name] = _witness(model, machine, [name]).get(name, "?")
            report.counterexamples.append(
                Counterexample(
                    kind="domain",
                    variable=name,
                    detail=f"can escape its emit domain {interval.text}",
                    witness=witness,
                )
            )
        solver.pop()

    if report.counterexamples:
        report.status = FALSIFIED
    return report


def falsify(funcs: Sequence[FunctionDef]) -> List[FunctionReport]:
    """Attempt to falsify every function in ``funcs``."""

    if z3 is None:
        raise FalsificationUnavailable(
            "z3-solver is not installed; install it with: pip install 'safelang[verify]'"
        )
    return [falsify_function(fn) for fn in funcs]


def format_reports(reports: Sequence[FunctionReport]) -> List[str]:
    """Render ``reports`` as human-readable CLI lines."""

    lines: List[str] = []
    for report in reports:
        if report.status == VERIFIED:
            suffix = f" ({'; '.join(report.notes)})" if report.notes else ""
            lines.append(f"OK: {report.name} survived falsification{suffix}")
            continue
        if report.status == FALSIFIED:
            for counterexample in report.counterexamples:
                lines.append(f"FALSIFIED: {report.name}: {counterexample.describe()}")
            continue
        lines.append(f"INCONCLUSIVE: {report.name}: body not fully modelled")
        for note in report.notes:
            lines.append(f"    {note}")
        for statement in report.unsupported:
            lines.append(f"    unsupported statement: {statement}")
    return lines


__all__ = [
    "Counterexample",
    "FalsificationUnavailable",
    "FunctionReport",
    "Interval",
    "falsify",
    "falsify_function",
    "format_reports",
    "parse_interval",
    "z3_available",
    "FALSIFIED",
    "INCONCLUSIVE",
    "VERIFIED",
]
