import pathlib
import subprocess
import pytest

RUNTIME_C_DIR = pathlib.Path(__file__).resolve().parent.parent / "runtime-c"
HARNESS = pathlib.Path(__file__).resolve().parent / "runtime_c_unsigned_harness.c"


def compile_and_run(macro: str, tmp_path):
    runtime = RUNTIME_C_DIR / "safelang_runtime.c"
    obj = tmp_path / "safelang_runtime.o"
    exe = tmp_path / "test"
    subprocess.check_call(["cc", "-std=c99", "-c", runtime, "-o", obj])
    subprocess.check_call(
        [
            "cc",
            "-std=c99",
            HARNESS,
            obj,
            f"-D{macro}",
            f"-I{RUNTIME_C_DIR}",
            "-o",
            exe,
        ]
    )
    proc = subprocess.run([exe], capture_output=True)
    assert proc.returncode < 0


@pytest.mark.parametrize(
    "macro", ["TEST_ADD", "TEST_SUB", "TEST_MUL", "TEST_DIV", "TEST_MOD"]
)
def test_negative_operands_abort(macro, tmp_path):
    compile_and_run(macro, tmp_path)
