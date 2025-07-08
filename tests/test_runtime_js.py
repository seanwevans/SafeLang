import json
import subprocess
from pathlib import Path

import safelang.runtime as rt

RUNTIME_JS = Path(__file__).resolve().parents[1] / "safelang" / "runtime.js"


def _call_js(func: str, a, b, bits: int, signed: bool = True):
    snippet = (
        f"const rt = require({json.dumps(str(RUNTIME_JS))});\n"
        f"const res = rt.{func}({a}, {b}, {bits}, {str(signed).lower()});\n"
        "console.log(JSON.stringify({value: res.value.toString(), saturated: res.saturated}));"
    )
    result = subprocess.run([
        "node",
        "-e",
        snippet,
    ], capture_output=True, text=True, check=True)
    out = json.loads(result.stdout.strip())
    return int(out["value"]), out["saturated"]


# Test satAdd

def test_sat_add_js_matches_py():
    cases = [
        (10, 5),
        (100, 100),
        (-100, -100),
    ]
    for a, b in cases:
        py_val, py_sat = rt.sat_add(a, b, 8, True)
        js_val, js_sat = _call_js("satAdd", a, b, 8, True)
        assert (js_val, js_sat) == (py_val, py_sat)


# Test satSub

def test_sat_sub_js_matches_py():
    cases = [
        (20, 10),
        (100, -100),
        (-100, 100),
    ]
    for a, b in cases:
        py_val, py_sat = rt.sat_sub(a, b, 8, True)
        js_val, js_sat = _call_js("satSub", a, b, 8, True)
        assert (js_val, js_sat) == (py_val, py_sat)


# Test satMul

def test_sat_mul_js_matches_py():
    cases = [
        (3, 4),
        (20, 20),
        (-20, 20),
    ]
    for a, b in cases:
        py_val, py_sat = rt.sat_mul(a, b, 8, True)
        js_val, js_sat = _call_js("satMul", a, b, 8, True)
        assert (js_val, js_sat) == (py_val, py_sat)


# Test satDiv

def test_sat_div_js_matches_py():
    cases = [
        (20, 5),
        (200, 1),
        (-200, 1),
    ]
    for a, b in cases:
        py_val, py_sat = rt.sat_div(a, b, 8, True)
        js_val, js_sat = _call_js("satDiv", a, b, 8, True)
        assert (js_val, js_sat) == (py_val, py_sat)


# Test satMod

def test_sat_mod_js_matches_py():
    cases = [
        (20, 6),
        (150, 200),
        (-150, -200),
    ]
    for a, b in cases:
        py_val, py_sat = rt.sat_mod(a, b, 8, True)
        js_val, js_sat = _call_js("satMod", a, b, 8, True)
        assert (js_val, js_sat) == (py_val, py_sat)
