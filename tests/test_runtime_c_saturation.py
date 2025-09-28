import pathlib
import subprocess

RUNTIME_C_DIR = pathlib.Path(__file__).resolve().parent.parent / "runtime-c"
HARNESS = pathlib.Path(__file__).resolve().parent / "runtime_c_saturation_harness.c"


def compile_and_run(tmp_path):
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
            f"-I{RUNTIME_C_DIR}",
            "-o",
            exe,
        ]
    )
    proc = subprocess.run([exe], capture_output=True, check=False)
    return proc.returncode


def test_unsigned_extreme_saturates(tmp_path):
    returncode = compile_and_run(tmp_path)
    assert returncode == 0
