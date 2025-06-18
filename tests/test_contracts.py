import os
import sys
import pytest

from safelang.parser import parse_functions, verify_contracts


def _verify(src: str):
    funcs = parse_functions(src)
    return verify_contracts(funcs)


def test_missing_space():
    src = 'function "foo" {\n@time 1ns\nconsume { nil }\nemit { nil }\n}'
    errors = _verify(src)
    assert errors == ["Function foo missing @space"]


def test_missing_time():
    src = 'function "bar" {\n@space 1B\nconsume { nil }\nemit { nil }\n}'
    errors = _verify(src)
    assert errors == ["Function bar missing @time"]


def test_missing_consume():
    src = 'function "baz" {\n@space 1B\n@time 1ns\nemit { nil }\n}'
    errors = _verify(src)
    assert errors == ["Function baz missing consume block"]


def test_missing_emit():
    src = 'function "qux" {\n@space 1B\n@time 1ns\nconsume { nil }\n}'
    errors = _verify(src)
    assert errors == ["Function qux missing emit block"]


def test_all_contracts_present():
    src = 'function "ok" {\n@space 1B\n@time 1ns\nconsume { nil }\nemit { nil }\n}'
    errors = _verify(src)
    assert errors == []
