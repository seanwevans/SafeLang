"""Static worst-case execution time estimation for SafeLang.

SafeLang functions declare a ``@time`` budget. This module is what makes that
declaration mean something: it walks a function body, adds up a cycle cost for
every operation it contains, converts the total to nanoseconds against a target
clock, and compares it against the declared budget.

The cost model is deliberately crude. It approximates a simple in-order core
with no cache, no pipeline overlap and no speculation, which is the machine a
hard-real-time budget is usually written against. It is *not* a substitute for
measuring on real silicon; it is a static, deterministic upper bound that
catches a budget nobody could possibly meet.

Two properties matter more than accuracy:

* It is **conservative about control flow**. A loop costs its full static trip
  count, and an ``if``/``else`` costs its more expensive arm.
* It **refuses to guess**. A loop whose bounds are not compile-time constants,
  or a construct the walker does not recognise, raises :class:`UnboundedError`
  rather than contributing a made-up number. An unbounded body has no worst
  case, and reporting one anyway would be worse than reporting nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .parser import FunctionDef, _sanitize

#: Default target clock. 100 MHz is a common microcontroller speed and makes
#: one cycle exactly 10ns, which keeps hand-checking the arithmetic easy.
DEFAULT_CLOCK_HZ = 100_000_000


class UnboundedError(ValueError):
    """Raised when a body has no statically provable worst case."""


@dataclass(frozen=True)
class CycleModel:
    """Cycle costs for the operations the estimator understands."""

    move: int = 1
    add: int = 1
    multiply: int = 3
    divide: int = 20
    compare: int = 1
    branch: int = 2
    index: int = 1
    call: int = 5
    ret: int = 1
    loop_setup: int = 1
    loop_step: int = 2

    def operator_cost(self, token: str) -> int:
        if token in {"+", "-"}:
            return self.add
        if token == "*":
            return self.multiply
        if token in {"/", "%"}:
            return self.divide
        if token in {"<", ">", "<=", ">=", "==", "!="}:
            return self.compare
        return 0


DEFAULT_MODEL = CycleModel()

_OPERATOR_RE = re.compile(r"<=|>=|==|!=|[-+*/%<>]")
_CALL_RE = re.compile(r"\b[A-Za-z_]\w*\s*\(")
_LOOP_RE = re.compile(r"^loop\s*\(\s*(\w+)\s*=\s*(.+?)\s*\.\.\s*(.+?)\s*\)\s*$")
_CASE_RE = re.compile(r"^case\b(?P<label>[^=]*)=>(?P<body>.*)$")
_INTEGER_RE = re.compile(r"^[+-]?\d+(?:_\d+)*$")


def parse_time_ns(value: str) -> int:
    """Parse a ``@time`` annotation such as ``10_000ns`` into nanoseconds."""

    match = re.fullmatch(r"([0-9_]+)ns", value.strip().lower())
    if not match:
        raise ValueError(f"Unrecognized time format: {value}")
    return int(match.group(1).replace("_", ""))


def _loop_bound(token: str) -> int:
    if not _INTEGER_RE.fullmatch(token):
        raise UnboundedError(
            f"loop bound {token!r} is not a compile-time constant; "
            "SafeLang loops must have statically provable bounds"
        )
    return int(token.replace("_", ""))


def _expression_cycles(expr: str, model: CycleModel) -> int:
    """Cost the operators, indexing and calls inside one expression."""

    cycles = 0
    for token in _OPERATOR_RE.findall(expr):
        cycles += model.operator_cost(token)
    cycles += expr.count("[") * model.index
    cycles += len(_CALL_RE.findall(expr)) * model.call
    return cycles


@dataclass
class _Line:
    indent: int
    text: str


def _body_lines(fn: FunctionDef) -> List[_Line]:
    """Return the executable lines of ``fn`` with their indentation."""

    lines: List[_Line] = []
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
        lines.append(_Line(indent=len(raw) - len(raw.lstrip()), text=stripped))
    return lines


def _statement_cycles(text: str, model: CycleModel) -> int:
    """Cost a single non-compound statement."""

    text = text.rstrip(";").strip()

    # `memory buffer[64] : f32` reserves space at @init time; SafeLang forbids
    # dynamic allocation, so the reservation itself costs nothing at runtime.
    if text.startswith("memory"):
        return 0

    if "?" in text:
        condition, _, action = text.partition("?")
        return (
            _expression_cycles(condition, model)
            + model.compare
            + model.branch
            + _statement_cycles(action, model)
        )

    if text.startswith("return"):
        return _expression_cycles(text[len("return") :], model) + model.ret

    return _expression_cycles(text, model) + model.move


def _block_cycles(
    lines: Sequence[_Line], start: int, indent: int, model: CycleModel
) -> Tuple[int, int]:
    """Cost the block of lines indented beyond ``indent``.

    Returns ``(cycles, next_index)``.
    """

    cycles = 0
    index = start
    while index < len(lines):
        line = lines[index]
        if line.indent <= indent:
            break

        loop_match = _LOOP_RE.match(line.text)
        if loop_match:
            low = _loop_bound(loop_match.group(2))
            high = _loop_bound(loop_match.group(3))
            # `loop(i = 0..9)` is inclusive of both ends.
            trips = max(0, high - low + 1)
            body_cycles, index = _block_cycles(lines, index + 1, line.indent, model)
            cycles += model.loop_setup + trips * (body_cycles + model.loop_step)
            continue

        if line.text.startswith("if "):
            cycles += (
                _expression_cycles(line.text[len("if ") :], model)
                + model.compare
                + model.branch
            )
            then_cycles, index = _block_cycles(lines, index + 1, line.indent, model)
            else_cycles = 0
            if (
                index < len(lines)
                and lines[index].indent == line.indent
                and lines[index].text == "else"
            ):
                else_cycles, index = _block_cycles(
                    lines, index + 1, lines[index].indent, model
                )
            # Only one arm runs, so the worst case is the pricier of the two.
            cycles += max(then_cycles, else_cycles)
            continue

        if line.text == "else":
            raise UnboundedError("'else' without a matching 'if'")

        if line.text.startswith("match "):
            cycles += _expression_cycles(line.text[len("match ") :], model)
            arm_cycles, index = _match_cycles(lines, index + 1, line.indent, model)
            cycles += arm_cycles
            continue

        cycles += _statement_cycles(line.text, model)
        index += 1

    return cycles, index


def _match_cycles(
    lines: Sequence[_Line], start: int, indent: int, model: CycleModel
) -> Tuple[int, int]:
    """Cost a ``match``: every arm is tested, the priciest arm is taken."""

    dispatch = 0
    worst_arm = 0
    index = start
    while index < len(lines):
        line = lines[index]
        if line.indent <= indent:
            break
        case_match = _CASE_RE.match(line.text)
        if not case_match:
            raise UnboundedError(f"unexpected statement inside match: {line.text!r}")

        dispatch += model.compare + model.branch
        arm = _expression_cycles(case_match.group("label"), model)
        inline = case_match.group("body").strip()
        if inline:
            arm += _statement_cycles(inline, model)
        nested, index = _block_cycles(lines, index + 1, line.indent, model)
        worst_arm = max(worst_arm, arm + nested)

    return dispatch + worst_arm, index


def estimate_cycles(fn: FunctionDef, model: CycleModel = DEFAULT_MODEL) -> int:
    """Return the worst-case cycle count for ``fn``'s body."""

    lines = _body_lines(fn)
    cycles, index = _block_cycles(lines, 0, -1, model)
    if index != len(lines):  # pragma: no cover - defensive
        raise UnboundedError(f"could not walk the whole body of {fn.name}")
    return cycles


def estimate_ns(
    fn: FunctionDef,
    clock_hz: int = DEFAULT_CLOCK_HZ,
    model: CycleModel = DEFAULT_MODEL,
) -> float:
    """Return the worst-case execution time of ``fn`` in nanoseconds."""

    if clock_hz <= 0:
        raise ValueError("clock_hz must be positive")
    return estimate_cycles(fn, model) * 1_000_000_000 / clock_hz


@dataclass
class TimingReport:
    """The WCET estimate for one function, next to its declared budget."""

    name: str
    cycles: int
    estimate_ns: float
    budget_ns: int

    @property
    def within_budget(self) -> bool:
        return self.estimate_ns <= self.budget_ns

    @property
    def headroom_ns(self) -> float:
        return self.budget_ns - self.estimate_ns

    def describe(self) -> str:
        verdict = "OK" if self.within_budget else "OVER"
        return (
            f"{verdict}: {self.name}: {self.cycles} cycles "
            f"= {self.estimate_ns:g}ns against a {self.budget_ns}ns budget"
        )


def analyze(
    funcs: Sequence[FunctionDef],
    clock_hz: int = DEFAULT_CLOCK_HZ,
    model: CycleModel = DEFAULT_MODEL,
) -> Tuple[List[TimingReport], List[str]]:
    """Estimate every function's WCET.

    Returns the reports that could be produced and the errors for the functions
    whose worst case could not be bounded.
    """

    reports: List[TimingReport] = []
    errors: List[str] = []
    for fn in funcs:
        try:
            budget = parse_time_ns(fn.time)
        except ValueError as exc:
            errors.append(f"Function {fn.name} {exc}")
            continue
        try:
            cycles = estimate_cycles(fn, model)
        except UnboundedError as exc:
            errors.append(f"Function {fn.name} has no bounded worst case: {exc}")
            continue
        reports.append(
            TimingReport(
                name=fn.name,
                cycles=cycles,
                estimate_ns=cycles * 1_000_000_000 / clock_hz,
                budget_ns=budget,
            )
        )
    return reports, errors


def check_time_budgets(
    funcs: Sequence[FunctionDef],
    clock_hz: int = DEFAULT_CLOCK_HZ,
    model: CycleModel = DEFAULT_MODEL,
) -> List[str]:
    """Return an error for every function that cannot meet its ``@time``."""

    reports, errors = analyze(funcs, clock_hz, model)
    for report in reports:
        if not report.within_budget:
            errors.append(
                f"Function {report.name} exceeds @time budget: "
                f"{report.cycles} cycles = {report.estimate_ns:g}ns at "
                f"{clock_hz / 1_000_000:g}MHz, budget is {report.budget_ns}ns"
            )
    return errors


__all__ = [
    "CycleModel",
    "DEFAULT_CLOCK_HZ",
    "DEFAULT_MODEL",
    "TimingReport",
    "UnboundedError",
    "analyze",
    "check_time_budgets",
    "estimate_cycles",
    "estimate_ns",
    "parse_time_ns",
]
