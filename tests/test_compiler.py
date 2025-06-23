from pathlib import Path
from safelang import parse_functions, compile_to_nasm


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
