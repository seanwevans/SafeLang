"""Command-line interface for the SafeLang demo compiler."""

import argparse
from pathlib import Path
import sys
from .parser import parse_functions, verify_contracts
from .compiler import compile_to_nasm, generate_c, generate_rust


def main() -> int:
    """Parse CLI arguments and verify a SafeLang source file."""
    parser = argparse.ArgumentParser(description="SafeLang demo verifier")
    parser.add_argument("file", type=Path, help="Path to SafeLang source")
    parser.add_argument("--nasm", type=Path, help="Write NASM output to file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--emit-c",
        action="store_true",
        help="Output generated C instead of verification result",
    )
    group.add_argument(
        "--emit-rust",
        action="store_true",
        help="Output generated Rust instead of verification result",
    )
    group.add_argument("--c-out", type=Path, help="Write generated C to file")
    group.add_argument("--rust-out", type=Path, help="Write generated Rust to file")
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

    if args.nasm:
        asm = compile_to_nasm(funcs)
        try:
            args.nasm.write_text(asm)
        except OSError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    try:
        if args.emit_c or args.c_out:
            code = generate_c(funcs)
            if args.c_out:
                try:
                    args.c_out.write_text(code)
                except OSError as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 1
            else:
                print(code)
        elif args.emit_rust or args.rust_out:
            code = generate_rust(funcs)
            if args.rust_out:
                try:
                    args.rust_out.write_text(code)
                except OSError as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 1
            else:
                print(code)
        else:
            print(f"Parsed {len(funcs)} functions successfully.")
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
