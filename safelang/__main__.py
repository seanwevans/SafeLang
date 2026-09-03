"""Command-line interface for the SafeLang demo compiler."""

import argparse
from pathlib import Path
import sys
from .parser import parse_functions, verify_contracts
from .compiler import compile_to_nasm, generate_c, generate_rust

#: Every code generator the CLI can drive, keyed by the name used in its flags.
#: Each backend gets the same pair of options: ``--emit-NAME`` writes to stdout
#: and ``--NAME-out PATH`` writes to a file.
_BACKENDS = {
    "c": ("C", generate_c),
    "rust": ("Rust", generate_rust),
    "nasm": ("NASM", compile_to_nasm),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SafeLang demo verifier")
    parser.add_argument("file", type=Path, help="Path to SafeLang source")

    group = parser.add_mutually_exclusive_group()
    for name, (label, _generator) in _BACKENDS.items():
        group.add_argument(
            f"--emit-{name}",
            action="store_true",
            help=f"Output generated {label} instead of verification result",
        )
        group.add_argument(
            f"--{name}-out",
            type=Path,
            help=f"Write generated {label} to file",
        )
    group.add_argument(
        "--nasm",
        type=Path,
        help="Deprecated alias for --nasm-out",
    )
    return parser


def _select_backend(args: argparse.Namespace):
    """Return ``(generator, destination)`` for the chosen output, if any.

    ``destination`` is ``None`` when the output goes to stdout.
    """

    for name, (_label, generator) in _BACKENDS.items():
        if getattr(args, f"emit_{name}"):
            return generator, None
        destination = getattr(args, f"{name}_out")
        if destination:
            return generator, destination

    if args.nasm:
        print(
            "WARNING: --nasm is deprecated, use --nasm-out instead",
            file=sys.stderr,
        )
        return compile_to_nasm, args.nasm

    return None, None


def main() -> int:
    """Parse CLI arguments and verify a SafeLang source file."""
    args = _build_parser().parse_args()

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

    generator, destination = _select_backend(args)
    if generator is None:
        print(f"Parsed {len(funcs)} functions successfully.")
        return 0

    try:
        code = generator(funcs)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if destination is None:
        print(code)
        return 0

    try:
        destination.write_text(code)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
