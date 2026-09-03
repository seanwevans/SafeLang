import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from safelang.parser import parse_functions
from safelang import adversary as adversary_module
from safelang.adversary import (
    FALSIFIED,
    INCONCLUSIVE,
    VERIFIED,
    FalsificationUnavailable,
    falsify,
    format_reports,
    parse_interval,
    z3_available,
)

pytestmark = pytest.mark.skipif(not z3_available(), reason="z3-solver is not installed")

ROOT = Path(__file__).resolve().parents[1]

BOOT = """
@init
function "boot" {
    @space 8B
    @time 10ns
    consume { nil }
    emit { nil }
}
"""


def _reports(body: str):
    return {report.name: report for report in falsify(parse_functions(BOOT + body))}


def test_parse_interval_closed():
    interval = parse_interval("[0, 1]")
    assert interval.lower == Fraction(0)
    assert interval.upper == Fraction(1)
    assert interval.lower_closed and interval.upper_closed


def test_parse_interval_half_open_and_fraction():
    interval = parse_interval("[0, 3/2)")
    assert interval.upper == Fraction(3, 2)
    assert interval.lower_closed
    assert not interval.upper_closed


def test_parse_interval_infinite_bound_is_unbounded():
    interval = parse_interval("[-inf, pi]")
    assert interval.lower is None
    assert interval.upper > Fraction(3)


def test_function_without_obligations_is_verified():
    report = _reports("")["boot"]
    assert report.status == VERIFIED
    assert report.notes == ["no emit domain obligations to falsify"]


def test_verified_function_survives():
    report = _reports(
        """
function "scale" {
    @space 16B
    @time 100ns
    consume {
        f32(ratio) # [0, 1]
    }
    scaled = ratio * 50
    emit {
        f32(scaled) # [0, 50]
    }
}
"""
    )["scale"]
    assert report.status == VERIFIED
    assert report.counterexamples == []


def test_domain_escape_is_falsified_with_a_witness():
    report = _reports(
        """
function "overshoot" {
    @space 16B
    @time 100ns
    consume {
        f32(input) # [0, 1]
    }
    result = input * 100
    emit {
        f32(result) # [0, 50]
    }
}
"""
    )["overshoot"]
    assert report.status == FALSIFIED
    (counterexample,) = report.counterexamples
    assert counterexample.kind == "domain"
    assert counterexample.variable == "result"
    assert "input" in counterexample.witness


def test_guarded_assignment_can_leave_a_variable_unassigned():
    report = _reports(
        """
function "partial" {
    @space 16B
    @time 100ns
    consume {
        f32(x) # [0, 2]
    }
    x < 0.1 ? cl_x = 0
    x > 1   ? cl_x = 1
    emit {
        f32(cl_x) # [0, 1]
    }
}
"""
    )["partial"]
    assert report.status == FALSIFIED
    assert any(c.kind == "unassigned" for c in report.counterexamples)


def test_default_before_guard_closes_the_gap():
    report = _reports(
        """
function "total" {
    @space 16B
    @time 100ns
    consume {
        f32(x) # [0, 3/2]
    }
    cl_x = x
    x > 1 ? cl_x = 1
    emit {
        f32(cl_x) # [0, 1]
    }
}
"""
    )["total"]
    assert report.status == VERIFIED


def test_variable_never_assigned_at_all():
    report = _reports(
        """
function "missing" {
    @space 16B
    @time 100ns
    consume {
        f32(x) # [0, 1]
    }
    y = x
    emit {
        f32(out) # [0, 1]
    }
}
"""
    )["missing"]
    assert report.status == FALSIFIED
    (counterexample,) = report.counterexamples
    assert counterexample.kind == "unassigned"
    assert counterexample.detail == "never assigned in the body"


def test_division_by_zero_is_reported():
    report = _reports(
        """
function "risky" {
    @space 16B
    @time 100ns
    consume {
        f32(num) # [1, 10]
        f32(den) # [-1, 1]
    }
    q = num / den
    emit {
        f32(q) # [-inf, inf]
    }
}
"""
    )["risky"]
    assert report.status == FALSIFIED
    assert any(c.kind == "division-by-zero" for c in report.counterexamples)


def test_division_by_a_nonzero_domain_is_safe():
    report = _reports(
        """
function "safe_div" {
    @space 16B
    @time 100ns
    consume {
        f32(num) # [0, 1]
        f32(den) # [1, 2]
    }
    q = num / den
    emit {
        f32(q) # [0, 1]
    }
}
"""
    )["safe_div"]
    assert report.status == VERIFIED


def test_return_binds_to_a_single_emit_variable():
    report = _reports(
        """
function "doubler" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, 4]
    }
    return a + a
    emit {
        f32(out) # [0, 8]
    }
}
"""
    )["doubler"]
    assert report.status == VERIFIED


def test_unmodelled_statement_makes_the_verdict_inconclusive():
    report = _reports(
        """
function "arrays" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, 1]
    }
    buffer[0] = a
    emit {
        f32(out) # [0, 1]
    }
}
"""
    )["arrays"]
    assert report.status == INCONCLUSIVE
    assert report.unsupported
    assert "buffer[0]" in report.unsupported[0]


def test_unmodelled_statement_does_not_hide_behind_a_pass():
    """A skipped statement must never be reported as a survived proof."""

    report = _reports(
        """
function "opaque" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, 1]
    }
    out = a
    hardware_poke(a)
    emit {
        f32(out) # [0, 1]
    }
}
"""
    )["opaque"]
    assert report.status == INCONCLUSIVE


def test_unresolvable_domain_endpoint_is_inconclusive():
    report = _reports(
        """
function "symbolic" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, MAX_THRUST]
    }
    out = a
    emit {
        f32(out) # [0, 1]
    }
}
"""
    )["symbolic"]
    assert report.status == INCONCLUSIVE
    assert report.notes


def test_format_reports_renders_each_status():
    reports = falsify(
        parse_functions(
            BOOT
            + """
function "overshoot" {
    @space 16B
    @time 100ns
    consume {
        f32(input) # [0, 1]
    }
    result = input * 100
    emit {
        f32(result) # [0, 50]
    }
}

function "arrays" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, 1]
    }
    buffer[0] = a
    emit {
        f32(out) # [0, 1]
    }
}
"""
        )
    )
    text = "\n".join(format_reports(reports))
    assert "OK: boot survived falsification" in text
    assert "FALSIFIED: overshoot: result:" in text
    assert "INCONCLUSIVE: arrays" in text
    assert "unsupported statement:" in text


def test_falsify_raises_without_z3(monkeypatch):
    monkeypatch.setattr(adversary_module, "z3", None)
    assert not adversary_module.z3_available()
    with pytest.raises(FalsificationUnavailable):
        adversary_module.falsify([])


def test_cli_falsify_accepts_the_verified_example():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safelang",
            "--falsify",
            str(ROOT / "example_verified.slang"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "survived falsification" in result.stdout


def test_cli_falsify_rejects_the_incomplete_example():
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--falsify", str(ROOT / "example.slang")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "FALSIFIED: clamp_params: cl_x" in result.stdout


# ``cl_x`` defaults to ``x`` over [0, 2], so a guard only survives if it fires
# for every ``x`` above 1.
@pytest.mark.parametrize(
    "guard, expected",
    [
        ("x >= 2", FALSIFIED),
        ("x <= 2", VERIFIED),
        ("x == 2", FALSIFIED),
        ("not (x < 2)", FALSIFIED),
        ("x > 1 and x > 0", VERIFIED),
        ("x > 5 or x > 1", VERIFIED),
        ("(x + 0) > 1", VERIFIED),
        ("x > +1", VERIFIED),
        ("-x < -1", VERIFIED),
    ],
)
def test_guard_operators_are_understood(guard, expected):
    report = _reports(
        f"""
function "guarded" {{
    @space 16B
    @time 100ns
    consume {{
        f32(x) # [0, 2]
    }}
    cl_x = x
    {guard} ? cl_x = 1
    emit {{
        f32(cl_x) # [0, 1]
    }}
}}
"""
    )["guarded"]
    assert report.status == expected


@pytest.mark.parametrize(
    "statement",
    [
        "out = a $ 2",
        "out = (a + 1",
        "out = a +",
        "out = inf",
        "out = a 2",
        "a > 0 ? out",
        "out = a > 0",
        "a + 1 ? out = a",
    ],
)
def test_unmodelled_expressions_are_inconclusive(statement):
    report = _reports(
        f"""
function "odd" {{
    @space 16B
    @time 100ns
    consume {{
        f32(a) # [0, 1]
    }}
    {statement}
    emit {{
        f32(out) # [0, 1]
    }}
}}
"""
    )["odd"]
    assert report.status == INCONCLUSIVE
    assert report.unsupported


def test_underscore_separated_literals_are_understood():
    report = _reports(
        """
function "scaled" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, 1]
    }
    out = a * 1_000
    emit {
        f32(out) # [0, 1_000]
    }
}
"""
    )["scaled"]
    assert report.status == VERIFIED


def test_pi_constant_agrees_between_domain_and_expression():
    report = _reports(
        """
function "circle" {
    @space 16B
    @time 100ns
    consume {
        f32(r) # [0, 1]
    }
    out = r * pi
    emit {
        f32(out) # [0, pi]
    }
}
"""
    )["circle"]
    assert report.status == VERIFIED


def test_division_under_a_guard_that_excludes_zero_is_safe():
    report = _reports(
        """
function "guarded_div" {
    @space 16B
    @time 100ns
    consume {
        f32(num) # [0, 1]
        f32(den) # [0, 2]
    }
    q = 0
    den > 1 ? q = num / den
    emit {
        f32(q) # [0, 1]
    }
}
"""
    )["guarded_div"]
    assert report.status == VERIFIED


def test_malformed_contract_entry_is_inconclusive():
    report = _reports(
        """
function "bad_contract" {
    @space 16B
    @time 100ns
    consume {
        f32(a) # [0, 1]
    }
    out = a
    emit {
        f32(out)
    }
}
"""
    )["bad_contract"]
    assert report.status == INCONCLUSIVE
    assert report.notes


def test_report_ok_property_tracks_status():
    reports = _reports("")
    assert reports["boot"].ok
