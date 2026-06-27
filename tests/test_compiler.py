import pytest

from safelang import parse_functions, compile_to_nasm
from safelang.compiler import (
    _parse_space,
    _compile_expr,
    _parse_params,
    _C_TYPE_MAP,
    _RUST_TYPE_MAP,
)


def test_compile_to_nasm(tmp_path):
    src = (
        "@init\n"
        'function "clamp_params_init" {\n'
        "    @space 512B\n"
        "    @time 10_000ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "    return 0\n"
        "}\n"
        'function "clamp_params" {\n'
        "    @space 128B\n"
        "    @time 1000ns\n"
        "    consume {\n"
        "        int64(x) # [0, 1]\n"
        "    }\n"
        "    emit {\n"
        "        int64(r) # [0, 1]\n"
        "    }\n"
        "    return x\n"
        "}\n"
    )
    funcs = parse_functions(src)
    asm = compile_to_nasm(funcs)
    assert "clamp_params_init:" in asm
    init_block = asm.split("clamp_params_init:")[1].split("clamp_params:")[0]
    assert "sub rsp, 512" in init_block
    params_block = asm.split("clamp_params:")[1]
    assert "sub rsp, 128" in params_block
    out = tmp_path / "out.asm"
    out.write_text(asm)
    assert out.read_text().startswith("; Auto-generated NASM")


def test_compile_expr_addition():
    var_regs = {"a": "rdi", "b": "rsi"}
    assert _compile_expr("a+b", var_regs) == ["mov rax, rdi", "add rax, rsi"]


def test_compile_expr_subtraction():
    var_regs = {"a": "rdi", "b": "rsi"}
    assert _compile_expr("a-b", var_regs) == ["mov rax, rdi", "sub rax, rsi"]


def test_compile_expr_unary_minus():
    var_regs = {"a": "rdi"}
    assert _compile_expr("-a", var_regs) == ["mov rax, 0", "sub rax, rdi"]


def test_parse_space_units():
    assert _parse_space("1B") == 1
    assert _parse_space("2KB") == 2 * 1024
    assert _parse_space("3MB") == 3 * 1024 * 1024


def test_parse_space_invalid():
    with pytest.raises(ValueError):
        _parse_space("10XB")
    with pytest.raises(ValueError):
        _parse_space("foo")


@pytest.mark.parametrize(
    "style,type_map", [("c", _C_TYPE_MAP), ("rust", _RUST_TYPE_MAP)]
)
def test_parse_params_duplicate_names(style, type_map):
    lines = ["int32(x)", "int32(x)"]
    with pytest.raises(ValueError):
        _parse_params(lines, type_map, style)


def test_compile_to_nasm_param_register_skips_nil():
    funcs = parse_functions(
        """
@init
function "nil_first" {
    @space 0B
    @time 1ns
    consume {
        nil
        int32(x)
    }
    emit {
        nil
    }
    return x;
}
"""
    )
    asm = compile_to_nasm(funcs)
    nil_first_block = asm.split("nil_first:", 1)[1]
    assert "mov rax, rdi" in nil_first_block
