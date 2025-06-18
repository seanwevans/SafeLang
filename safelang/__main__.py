"""Command-line interface for the SafeLang demo compiler."""

import argparse
from pathlib import Path
from .parser import parse_functions, verify_contracts


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeLang demo verifier")
    parser.add_argument("file", type=Path, help="Path to SafeLang source")
    args = parser.parse_args()

    text = args.file.read_text()
    funcs = parse_functions(text)
    errors = verify_contracts(funcs)

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print(f"Parsed {len(funcs)} functions successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
