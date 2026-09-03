import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_valid():
    file = Path(__file__).resolve().parents[1] / "example.slang"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", str(file)], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Parsed" in result.stdout


def test_cli_invalid(tmp_path):
    invalid_src = (
        'function "foo" {\n'
        "    @space 128B\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "}\n"
    )
    invalid_file = tmp_path / "invalid.slang"
    invalid_file.write_text(invalid_src)
    result = subprocess.run(
        [sys.executable, "-m", "safelang", str(invalid_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ERROR" in result.stdout


def test_cli_parse_error(tmp_path):
    invalid_src = 'function "foo" {'
    invalid_file = tmp_path / "bad.slang"
    invalid_file.write_text(invalid_src)
    result = subprocess.run(
        [sys.executable, "-m", "safelang", str(invalid_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_cli_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.slang"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", str(missing)], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_cli_emit_c():
    file = Path(__file__).resolve().parents[1] / "example.slang"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--emit-c", str(file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "#include <stdint.h>" in result.stdout
    assert "typedef struct clamp_params_emit_t {" in result.stdout
    assert (
        "clamp_params_emit_t clamp_params(float x, float y, float z)" in result.stdout
    )


def test_cli_emit_rust():
    file = Path(__file__).resolve().parents[1] / "example.slang"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--emit-rust", str(file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (
        "pub fn clamp_params(x: f32, y: f32, z: f32) -> (f32, f32, f32)"
        in result.stdout
    )


def test_cli_c_out(tmp_path):
    file = Path(__file__).resolve().parents[1] / "example.slang"
    out_file = tmp_path / "out.c"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--c-out", str(out_file), str(file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert "#include <stdint.h>" in out_file.read_text()
    assert "typedef struct clamp_params_emit_t {" in out_file.read_text()


def test_cli_rust_out(tmp_path):
    file = Path(__file__).resolve().parents[1] / "example.slang"
    out_file = tmp_path / "out.rs"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--rust-out", str(out_file), str(file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert (
        "pub fn clamp_params(x: f32, y: f32, z: f32) -> (f32, f32, f32)"
        in out_file.read_text()
    )


def test_cli_emit_c_malformed(tmp_path):
    malformed_src = (
        "@init\n"
        'function "init" {\n'
        "    @space 1B\n"
        "    @time 1ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "}\n"
        'function "foo" {\n'
        "    @space 1B\n"
        "    @time 1ns\n"
        "    consume { int64 x }\n"
        "    emit { nil }\n"
        "}\n"
    )
    malformed_file = tmp_path / "malformed.slang"
    malformed_file.write_text(malformed_src)
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--emit-c", str(malformed_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ERROR" in result.stdout


def test_cli_emit_nasm(tmp_path):
    src = (
        "@init\n"
        'function "init" {\n'
        "    @space 1B\n"
        "    @time 100ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "    return 0\n"
        "}\n"
        'function "add" {\n'
        "    @space 1B\n"
        "    @time 100ns\n"
        "    consume {\n"
        "        int64(a) # [0, 100]\n"
        "        int64(b) # [0, 100]\n"
        "    }\n"
        "    emit {\n"
        "        int64(r) # [0, 200]\n"
        "    }\n"
        "    return a + b\n"
        "}\n"
    )
    src_file = tmp_path / "ok.slang"
    src_file.write_text(src)
    out_file = tmp_path / "out.asm"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--nasm", str(out_file), str(src_file)]
    )
    assert result.returncode == 0
    assert out_file.read_text().startswith("; Auto-generated NASM")


def test_cli_emit_nasm_unsupported_input(tmp_path):
    src = (
        "@init\n"
        'function "init" {\n'
        "    @space 1B\n"
        "    @time 100ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "    return 0\n"
        "}\n"
        'function "badnasm" {\n'
        "    @space 1B\n"
        "    @time 100ns\n"
        "    consume {\n"
        "        int64(a) # [0, 100]\n"
        "    }\n"
        "    emit {\n"
        "        int64(r) # [0, 100]\n"
        "    }\n"
        "    a = a + 1\n"
        "}\n"
    )
    src_file = tmp_path / "badnasm.slang"
    out_file = tmp_path / "out.asm"
    src_file.write_text(src)
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--nasm", str(out_file), str(src_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ERROR:" in result.stderr
    assert "badnasm: unsupported statement" in result.stderr
    assert not out_file.exists()


def test_cli_emit_conflict():
    file = Path(__file__).resolve().parents[1] / "example.slang"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safelang",
            "--emit-c",
            "--emit-rust",
            str(file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr.lower()


NASM_SRC = (
    "@init\n"
    'function "init" {\n'
    "    @space 1B\n"
    "    @time 1ns\n"
    "    consume { nil }\n"
    "    emit { nil }\n"
    "    return 0\n"
    "}\n"
    'function "add" {\n'
    "    @space 1B\n"
    "    @time 1ns\n"
    "    consume {\n"
    "        int64(a) # [0, 100]\n"
    "        int64(b) # [0, 100]\n"
    "    }\n"
    "    emit {\n"
    "        int64(r) # [0, 200]\n"
    "    }\n"
    "    return a + b\n"
    "}\n"
)


def test_cli_emit_nasm_to_stdout(tmp_path):
    src_file = tmp_path / "ok.slang"
    src_file.write_text(NASM_SRC)
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--emit-nasm", str(src_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("; Auto-generated NASM")
    assert "global add" in result.stdout


def test_cli_nasm_out_writes_a_file(tmp_path):
    src_file = tmp_path / "ok.slang"
    src_file.write_text(NASM_SRC)
    out_file = tmp_path / "out.asm"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--nasm-out", str(out_file), str(src_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert out_file.read_text().startswith("; Auto-generated NASM")


def test_cli_nasm_alias_still_works_but_warns(tmp_path):
    src_file = tmp_path / "ok.slang"
    src_file.write_text(NASM_SRC)
    out_file = tmp_path / "out.asm"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--nasm", str(out_file), str(src_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--nasm is deprecated" in result.stderr
    assert out_file.read_text().startswith("; Auto-generated NASM")


def test_cli_emit_nasm_unsupported_input_to_stdout(tmp_path):
    src = (
        "@init\n"
        'function "init" {\n'
        "    @space 1B\n"
        "    @time 1ns\n"
        "    consume { nil }\n"
        "    emit { nil }\n"
        "}\n"
        'function "badnasm" {\n'
        "    @space 1B\n"
        "    @time 1ns\n"
        "    consume {\n"
        "        int64(a) # [0, 100]\n"
        "    }\n"
        "    emit {\n"
        "        int64(r) # [0, 100]\n"
        "    }\n"
        "    a = a + 1\n"
        "}\n"
    )
    src_file = tmp_path / "badnasm.slang"
    src_file.write_text(src)
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--emit-nasm", str(src_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "badnasm: unsupported statement" in result.stderr
    assert result.stdout == ""


def test_cli_nasm_out_unwritable_path(tmp_path):
    src_file = tmp_path / "ok.slang"
    src_file.write_text(NASM_SRC)
    out_file = tmp_path / "missing-dir" / "out.asm"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--nasm-out", str(out_file), str(src_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "ERROR" in result.stderr
    assert not out_file.exists()


@pytest.mark.parametrize(
    "flags",
    [
        ("--emit-c", "--emit-nasm"),
        ("--emit-nasm", "--emit-rust"),
        ("--emit-nasm", "--nasm-out", "out.asm"),
        ("--nasm", "out.asm", "--nasm-out", "out2.asm"),
        ("--c-out", "out.c", "--emit-nasm"),
    ],
)
def test_cli_output_flags_are_mutually_exclusive(flags):
    file = Path(__file__).resolve().parents[1] / "example.slang"
    result = subprocess.run(
        [sys.executable, "-m", "safelang", *flags, str(file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr
