"""The wall-time simulator must keep quoting the compiler, not itself.

``docs/index.html`` draws a cycle count, a worst-case execution time and a
``@time`` budget for every function in its control frame, and states that those
numbers came out of ``safelang --time-report``. Nothing stops the two from
drifting apart once the cost model changes, so this module re-derives every
number from ``docs/sim.slang`` and fails when the page disagrees.
"""

import re
from pathlib import Path

import pytest

from safelang.adversary import FALSIFIED, VERIFIED, falsify, z3_available
from safelang.parser import parse_functions
from safelang.runtime import bounds
from safelang.timing import DEFAULT_CLOCK_HZ, analyze, parse_time_ns

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "index.html"
SIM = ROOT / "docs" / "sim.slang"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _js_const(name: str) -> int:
    """Read a numeric ``const NAME = 123;`` out of the page."""
    match = re.search(rf"^const {name} = (-?\d+);", _page(), re.MULTILINE)
    assert match, f"{name} not found in {PAGE.name}"
    return int(match.group(1))


def _tasks() -> list[dict]:
    """Read the page's TASKS table."""
    match = re.search(r"^const TASKS = \[(.*?)^\];", _page(), re.MULTILINE | re.DOTALL)
    assert match, f"TASKS not found in {PAGE.name}"
    tasks = []
    for row in re.finditer(r"\{([^}]*)\}", match.group(1)):
        entry = {}
        for key, value in re.findall(r"(\w+):\s*('[^']*'|-?\d+)", row.group(1)):
            entry[key] = value[1:-1] if value.startswith("'") else int(value)
        tasks.append(entry)
    assert tasks, "TASKS parsed empty"
    return tasks


def _reports():
    return {r.name: r for r in analyze(parse_functions(SIM.read_text()))[0]}


def test_sim_source_analyses_cleanly():
    reports, errors = analyze(parse_functions(SIM.read_text()))
    assert errors == []
    assert all(r.within_budget for r in reports), [r.describe() for r in reports]


@pytest.mark.parametrize("task", _tasks(), ids=lambda t: t["name"])
def test_page_quotes_the_analyser(task):
    """Every cycle count and WCET drawn on the page is the analyser's own."""
    report = _reports()[task["name"]]
    assert task["cyc"] == report.cycles
    assert task["wcet"] == pytest.approx(report.estimate_ns)
    assert task["budget"] == report.budget_ns


def test_page_best_case_never_exceeds_the_bound():
    """The page animates a per-frame cost between `best` and `wcet`."""
    for task in _tasks():
        assert 0 < task["best"] <= task["wcet"], task


def test_schedule_fits_inside_its_period():
    """The page draws the budgets packed end to end inside one period."""
    total = sum(t["budget"] for t in _tasks())
    period = _js_const("PERIOD_NS")
    assert total <= period, f"declared budgets {total}ns overrun the {period}ns period"


def test_rejected_function_matches_the_examples():
    """The panel struck from the schedule is the one the examples falsify."""
    page = _page()
    match = re.search(r"^const REJECTED = \{([^}]*)\}", page, re.MULTILINE)
    assert match, "REJECTED not found"
    fields = dict(re.findall(r"(\w+):\s*'([^']*)'", match.group(1)))
    assert fields["name"] == "clamp_params"
    assert fields["witness"] == "x=0.1"

    cycles = int(re.search(r"cyc:(\d+)", match.group(1)).group(1))
    budget = int(re.search(r"budget:(\d+)", match.group(1)).group(1))
    reports = {
        r.name: r
        for r in analyze(parse_functions((ROOT / "example.slang").read_text()))[0]
    }
    assert reports["clamp_params"].cycles == cycles
    assert reports["clamp_params"].budget_ns == budget


@pytest.mark.skipif(not z3_available(), reason="z3-solver is not installed")
def test_adversary_panel_still_shows_the_real_verdicts():
    """The two contracts the ADVERSARY panel draws must still hold those verdicts."""
    verdicts = {
        r.name: r.status
        for r in falsify(parse_functions((ROOT / "example.slang").read_text()))
    }
    assert verdicts["clamp_params"] == FALSIFIED

    survivors = {
        r.name: r.status
        for r in falsify(parse_functions((ROOT / "example_verified.slang").read_text()))
    }
    assert survivors["clamp_unit"] == VERIFIED


def test_page_uses_the_runtime_int16_bounds():
    """The RAIL panel clamps and wraps at the runtime's own int16 limits."""
    minimum, maximum = bounds(16, signed=True)
    assert _js_const("I16_MAX") == maximum
    assert _js_const("I16_MIN") == minimum


def test_page_clock_matches_the_timing_default():
    """The page's ns figures assume the analyser's default 100 MHz clock."""
    assert _js_const("CLOCK_MHZ") * 1_000_000 == DEFAULT_CLOCK_HZ


def test_init_budget_is_declared_in_nanoseconds():
    """@init is parsed by the same code path the page's arena burst stands for."""
    init = [f for f in parse_functions(SIM.read_text()) if f.is_init]
    assert len(init) == 1
    assert parse_time_ns(init[0].time) > 0
