import pathlib
import subprocess


RUNTIME_C_DIR = pathlib.Path(__file__).resolve().parent.parent / "runtime-c"
HARNESS = pathlib.Path(__file__).resolve().parent / "runtime_c_bounds_harness.c"


def test_sl_bounds_high_bitwidth(tmp_path):
    runtime = RUNTIME_C_DIR / "safelang_runtime.c"
    obj = tmp_path / "safelang_runtime.o"
    exe = tmp_path / "test_bounds"

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

    proc = subprocess.run([exe])
    assert proc.returncode == 0
