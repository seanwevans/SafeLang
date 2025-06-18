from pathlib import Path
from safelang import parse_functions, compile_to_nasm


def test_compile_to_nasm(tmp_path):
    src = Path(__file__).resolve().parents[1] / "example.slang"
    funcs = parse_functions(src.read_text())
    asm = compile_to_nasm(funcs)
    assert "clamp_params_init:" in asm
    out = tmp_path / "out.asm"
    out.write_text(asm)
    assert out.read_text().startswith("; Auto-generated NASM")
