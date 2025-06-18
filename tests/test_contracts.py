from safelang.parser import parse_functions, verify_contracts

BASE_INIT = (
    '@init\nfunction "init" {\n'
    "@space 1B\n"
    "@time 1ns\n"
    "consume { nil }\n"
    "emit { nil }\n"
    "}\n"
)


def _verify(src: str, include_init: bool = True):
    if include_init:
        src = BASE_INIT + src
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


def test_no_init_function():
    src = 'function "foo" {\n@space 1B\n@time 1ns\nconsume { nil }\nemit { nil }\n}'
    errors = _verify(src, include_init=False)
    assert errors == ["No @init function defined"]


def test_multiple_init_functions():
    src = (
        '@init\nfunction "i1" {\n@space 1B\n@time 1ns\nconsume { nil }\nemit { nil }\n}'
        '\n@init\nfunction "i2" {\n@space 1B\n@time 1ns\nconsume { nil }\nemit { nil }\n}'
    )
    errors = _verify(src, include_init=False)
    assert errors == ["Multiple @init functions defined"]
