from pathlib import Path

import pytest

from safelang import parse_functions, compile_to_nasm
from safelang.compiler import _parse_space, _compile_expr


def test_compile_to_nasm(tmp_path):
    src = Path(__file__).resolve().parents[1] / "example.slang"
    funcs = parse_functions(src.read_text())
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
