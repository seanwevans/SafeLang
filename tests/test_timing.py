import subprocess
import sys
from pathlib import Path

import pytest

from safelang.parser import parse_functions
from safelang.timing import (
    DEFAULT_CLOCK_HZ,
    CycleModel,
    TimingReport,
    UnboundedError,
    analyze,
    check_time_budgets,
    estimate_cycles,
    estimate_ns,
    parse_time_ns,
)

ROOT = Path(__file__).resolve().parents[1]

BOOT = """
@init
function "boot" {
    @space 8B
    @time 1000ns
    consume { nil }
    emit { nil }
}
"""


def _function(body: str, budget: str = "1000ns", name: str = "subject"):
    source = (
        f'function "{name}" {{\n'
        f"    @space 32B\n"
        f"    @time {budget}\n"
        f"    consume {{ nil }}\n"
        f"    emit {{ nil }}\n"
        f"{body}\n"
        f"}}\n"
    )
    return parse_functions(source)[0]


def test_parse_time_ns_accepts_underscores():
    assert parse_time_ns("10_000ns") == 10000


def test_parse_time_ns_is_case_insensitive():
    assert parse_time_ns("500NS") == 500


@pytest.mark.parametrize("value", ["", "10", "10us", "ns", "1.5ns"])
def test_parse_time_ns_rejects_bad_formats(value):
    with pytest.raises(ValueError):
        parse_time_ns(value)


def test_empty_body_costs_nothing():
    assert estimate_cycles(_function("")) == 0


def test_assignment_costs_a_move():
    assert estimate_cycles(_function("    out = a")) == 1


def test_operators_are_priced_by_the_model():
    model = CycleModel()
    assert estimate_cycles(_function("    out = a + b")) == model.add + model.move
    assert estimate_cycles(_function("    out = a * b")) == model.multiply + model.move
    assert estimate_cycles(_function("    out = a / b")) == model.divide + model.move


def test_memory_declarations_are_free():
    assert estimate_cycles(_function("    memory buffer[64] : f32")) == 0


def test_array_indexing_costs_an_address_computation():
    model = CycleModel()
    assert estimate_cycles(_function("    buffer[0] = 1")) == model.index + model.move


def test_calls_are_priced():
    model = CycleModel()
    assert estimate_cycles(_function("    out = poke(a)")) == model.call + model.move


def test_guarded_assignment_pays_for_the_test_and_the_branch():
    model = CycleModel()
    expected = model.compare * 2 + model.branch + model.move
    assert estimate_cycles(_function("    a > 1 ? out = 0")) == expected


def test_return_costs_a_return():
    model = CycleModel()
    assert estimate_cycles(_function("    return a + b")) == model.add + model.ret


def test_loop_multiplies_its_body_by_the_trip_count():
    model = CycleModel()
    body = "    loop(i = 0..9)\n        acc = acc + a"
    per_iteration = model.add + model.move + model.loop_step
    assert estimate_cycles(_function(body)) == model.loop_setup + 10 * per_iteration


def test_loop_bounds_are_inclusive():
    single = estimate_cycles(_function("    loop(i = 0..0)\n        a = a"))
    double = estimate_cycles(_function("    loop(i = 0..1)\n        a = a"))
    assert double - single == estimate_cycles(_function("    a = a")) + 2


def test_nested_loops_multiply():
    body = "    loop(i = 0..3)\n        loop(j = 0..4)\n            a = a"
    model = CycleModel()
    inner = model.loop_setup + 5 * (model.move + model.loop_step)
    outer = model.loop_setup + 4 * (inner + model.loop_step)
    assert estimate_cycles(_function(body)) == outer


def test_loop_with_a_non_constant_bound_has_no_worst_case():
    with pytest.raises(UnboundedError, match="statically provable bounds"):
        estimate_cycles(_function("    loop(i = 0..n)\n        a = a"))


def test_if_else_costs_the_more_expensive_arm():
    cheap = "    if a > 0\n        out = a\n    else\n        out = a * a * a"
    flipped = "    if a > 0\n        out = a * a * a\n    else\n        out = a"
    assert estimate_cycles(_function(cheap)) == estimate_cycles(_function(flipped))


def test_if_without_else_still_pays_for_the_test():
    model = CycleModel()
    body = "    if a > 0\n        out = a"
    expected = model.compare * 2 + model.branch + model.move
    assert estimate_cycles(_function(body)) == expected


def test_dangling_else_is_rejected():
    with pytest.raises(UnboundedError, match="without a matching"):
        estimate_cycles(_function("    else\n        out = a"))


def test_match_tests_every_arm_and_takes_the_worst():
    model = CycleModel()
    body = "    match sel\n        case A => out = a\n        case B => out = a * a * a"
    dispatch = 2 * (model.compare + model.branch)
    worst = model.multiply * 2 + model.move
    assert estimate_cycles(_function(body)) == dispatch + worst


def test_match_with_a_nested_arm_body():
    body = "    match sel\n        case A =>\n            out = a + a\n        case B => out = a"
    model = CycleModel()
    dispatch = 2 * (model.compare + model.branch)
    worst = model.add + model.move
    assert estimate_cycles(_function(body)) == dispatch + worst


def test_non_case_statement_inside_match_is_rejected():
    with pytest.raises(UnboundedError, match="inside match"):
        estimate_cycles(_function("    match sel\n        out = a"))


def test_estimate_ns_scales_with_the_clock():
    fn = _function("    out = a + b")
    assert estimate_ns(fn, clock_hz=100_000_000) == 20.0
    assert estimate_ns(fn, clock_hz=200_000_000) == 10.0


def test_estimate_ns_rejects_a_non_positive_clock():
    with pytest.raises(ValueError, match="must be positive"):
        estimate_ns(_function("    out = a"), clock_hz=0)


def test_a_custom_model_changes_the_estimate():
    fn = _function("    out = a * b")
    assert estimate_cycles(fn, CycleModel(multiply=1)) == 2


def test_check_time_budgets_passes_a_realistic_budget():
    funcs = parse_functions(BOOT) + [_function("    out = a + b", budget="1000ns")]
    assert check_time_budgets(funcs) == []


def test_check_time_budgets_rejects_an_impossible_budget():
    funcs = [_function("    out = a * b * b", budget="1ns")]
    (error,) = check_time_budgets(funcs)
    assert "exceeds @time budget" in error
    assert "budget is 1ns" in error


def test_a_faster_clock_can_bring_a_function_into_budget():
    funcs = [_function("    out = a + b", budget="15ns")]
    assert check_time_budgets(funcs, clock_hz=100_000_000)
    assert check_time_budgets(funcs, clock_hz=1_000_000_000) == []


def test_analyze_reports_an_unparsable_budget():
    fn = _function("    out = a", budget="1us")
    reports, errors = analyze([fn])
    assert reports == []
    assert "Unrecognized time format" in errors[0]


def test_analyze_reports_an_unbounded_body():
    fn = _function("    loop(i = 0..n)\n        a = a")
    reports, errors = analyze([fn])
    assert reports == []
    assert "no bounded worst case" in errors[0]


def test_timing_report_headroom():
    report = TimingReport(name="f", cycles=2, estimate_ns=20.0, budget_ns=100)
    assert report.within_budget
    assert report.headroom_ns == 80.0
    assert report.describe().startswith("OK: f: 2 cycles")


def test_timing_report_over_budget_describes_itself():
    report = TimingReport(name="f", cycles=200, estimate_ns=2000.0, budget_ns=100)
    assert not report.within_budget
    assert report.describe().startswith("OVER: f:")


def test_default_clock_makes_one_cycle_ten_nanoseconds():
    assert DEFAULT_CLOCK_HZ == 100_000_000
    assert estimate_ns(_function("    out = a")) == 10.0


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "safelang", *args], capture_output=True, text=True
    )


def test_cli_time_report_lists_every_function():
    result = _run_cli("--time-report", str(ROOT / "example.slang"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: clamp_params_init:" in result.stdout
    assert "OK: clamp_params:" in result.stdout


def test_cli_rejects_an_unmeetable_budget(tmp_path):
    source = tmp_path / "tight.slang"
    source.write_text(
        BOOT + 'function "tight" {\n'
        "    @space 32B\n"
        "    @time 1ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "    out = a * b * b\n"
        "}\n"
    )
    result = _run_cli(str(source))
    assert result.returncode == 1
    assert "exceeds @time budget" in result.stdout


def test_cli_no_time_check_skips_the_analysis(tmp_path):
    source = tmp_path / "tight.slang"
    source.write_text(
        BOOT + 'function "tight" {\n'
        "    @space 32B\n"
        "    @time 1ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "    out = a * b * b\n"
        "}\n"
    )
    assert _run_cli("--no-time-check", str(source)).returncode == 0


def test_cli_clock_mhz_changes_the_verdict(tmp_path):
    source = tmp_path / "tight.slang"
    source.write_text(
        BOOT + 'function "tight" {\n'
        "    @space 32B\n"
        "    @time 15ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "    out = a + b\n"
        "}\n"
    )
    assert _run_cli(str(source)).returncode == 1
    assert _run_cli("--clock-mhz", "1000", str(source)).returncode == 0


def test_cli_rejects_a_non_positive_clock():
    result = _run_cli("--clock-mhz", "0", str(ROOT / "example.slang"))
    assert result.returncode == 1
    assert "--clock-mhz must be positive" in result.stderr


def test_multiline_contract_blocks_are_not_counted_as_work():
    source = (
        'function "contracted" {\n'
        "    @space 32B\n"
        "    @time 1000ns\n"
        "    consume {\n"
        "        f32(a) # [0, 1]\n"
        "        f32(b) # [0, 1]\n"
        "    }\n"
        "    out = a + b\n"
        "    emit {\n"
        "        f32(out) # [0, 2]\n"
        "    }\n"
        "}\n"
    )
    model = CycleModel()
    fn = parse_functions(source)[0]
    assert estimate_cycles(fn) == model.add + model.move


def test_unknown_operator_tokens_are_free():
    assert CycleModel().operator_cost("@") == 0
