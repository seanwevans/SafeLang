"""Command-line interface for the SafeLang demo compiler."""

import argparse
from pathlib import Path
import sys
from .parser import parse_functions, verify_contracts
from .compiler import generate_c, generate_rust
from .compiler import compile_to_nasm
from .compiler import generate_c


def main() -> int:
    """Parse CLI arguments and verify a SafeLang source file."""
    parser = argparse.ArgumentParser(description="SafeLang demo verifier")
    parser.add_argument("file", type=Path, help="Path to SafeLang source")
    parser.add_argument("--nasm", type=Path, help="Write NASM output to file")
    parser.add_argument(
        "--emit-c",
        action="store_true",
        help="Output generated C instead of verification result",
    )
    parser.add_argument(
        "--emit-rust",
        action="store_true",
        help="Output generated Rust instead of verification result",
    )
    args = parser.parse_args()

    try:
        text = args.file.read_text()
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        funcs = parse_functions(text)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    errors = verify_contracts(funcs)

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print(f"Parsed {len(funcs)} functions successfully.")

    if args.nasm:
        asm = compile_to_nasm(funcs)
        try:
            args.nasm.write_text(asm)
        except OSError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    if args.emit_c:
        print(generate_c(funcs))
    elif args.emit_rust:
        print(generate_rust(funcs))
    else:
        print(f"Parsed {len(funcs)} functions successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
