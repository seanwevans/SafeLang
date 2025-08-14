import subprocess
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_C = ROOT / "runtime-c" / "safelang_runtime.c"
INCLUDE_DIR = ROOT / "runtime-c"

def run_program(source: str) -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "test.c"
        src_path.write_text(source)
        exe_path = Path(tmpdir) / "test"
        subprocess.run([
            "cc",
            src_path,
            str(RUNTIME_C),
            "-I",
            str(INCLUDE_DIR),
            "-o",
            exe_path,
        ], check=True)
        result = subprocess.run([exe_path])
        return result.returncode

@pytest.mark.parametrize("a,b", [(-1,1),(1,-1)])
@pytest.mark.parametrize("func", ["add", "sub", "mul", "div", "mod"])
def test_unsigned_negative_operands(func, a, b):
    call = f"sl_sat_{func}({a}, {b}, 8, false);"
    source = f"""
#include \"safelang_runtime.h\"
int main() {{
    {call}
    return 0;
}}
"""
    rc = run_program(source)
    assert rc == -6
