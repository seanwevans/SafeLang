import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from safelang.parser import parse_functions

EXAMPLE_TEXT = open('example.slang').read()

def test_parse_example():
    funcs = parse_functions(EXAMPLE_TEXT)
    assert len(funcs) == 2
    names = [f.name for f in funcs]
    assert 'clamp_params_init' in names
    assert 'clamp_params' in names


def test_init_without_function():
    with pytest.raises(ValueError):
        parse_functions('@init')


def test_unterminated_block():
    src = 'function "foo" {\n    @space 1B'
    with pytest.raises(ValueError):
        parse_functions(src)


def test_unmatched_closing_brace():
    src = 'function "foo" }'
    with pytest.raises(ValueError):
        parse_functions(src)


def test_nested_braces():
    src = 'function "foo" { if { } }'
    funcs = parse_functions(src)
    assert len(funcs) == 1
=======
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from pathlib import Path
from safelang import parse_functions


def test_parse_example():
    text = Path("example.slang").read_text()
    funcs = parse_functions(text)
    assert len(funcs) == 2

    init_fn = funcs[0]
    assert init_fn.name == "clamp_params_init"
    assert init_fn.space == "512B"
    assert init_fn.time == "10_000ns"
    assert init_fn.consume == ["nil"]
    assert init_fn.emit == ["nil"]

    clamp_fn = funcs[1]
    assert clamp_fn.name == "clamp_params"
    assert clamp_fn.space == "128B"
    assert clamp_fn.time == "1000ns"
    assert clamp_fn.consume == [
        "f32(x) # [0, 3/2]       ! 0 \u2264 x \u2264 1.5",
        "f32(y) # [-3, 4.29382)  ! -3 \u2264 y < 4.29382",
        "f32(z) # [-inf, pi]     ! -\u221e \u2264 z \u2264 \u03c0",
    ]
    assert clamp_fn.emit == [
        "f32(cl_x) # [0, 1]",
        "f32(cl_y) # [-3, 3]",
        "f32(cl_z) # [-1.1, 2]",
    ]