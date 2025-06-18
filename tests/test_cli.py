import subprocess
import sys
from pathlib import Path


def test_cli_valid():
    file = Path('example.slang')
    result = subprocess.run([sys.executable, '-m', 'safelang', str(file)], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Parsed' in result.stdout


def test_cli_invalid(tmp_path):
    invalid_src = (
        'function "foo" {\n'
        '    @space 128B\n'
        '    consume { nil }\n'
        '    emit { nil }\n'
        '}\n'
    )
    invalid_file = tmp_path / 'invalid.slang'
    invalid_file.write_text(invalid_src)
    result = subprocess.run([sys.executable, '-m', 'safelang', str(invalid_file)], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'ERROR' in result.stdout
