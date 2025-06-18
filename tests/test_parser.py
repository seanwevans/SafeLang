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


def test_braces_in_comment():
    src = 'function "foo" { ! { comment }\n }'
    funcs = parse_functions(src)
    assert len(funcs) == 1


def test_braces_in_string():
    src = 'function "foo" { msg = "{ not a brace }" }'
    funcs = parse_functions(src)
    assert len(funcs) == 1
