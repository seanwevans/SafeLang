"""Command-line interface for the SafeLang demo compiler."""

import argparse
from pathlib import Path
import sys
from . import __version__
from .parser import parse_functions, verify_contracts
from .compiler import compile_to_nasm, generate_c, generate_rust
from .timing import DEFAULT_CLOCK_HZ, analyze, check_time_budgets


def main() -> int:
    """Parse CLI arguments and verify a SafeLang source file."""
    parser = argparse.ArgumentParser(description="SafeLang demo verifier")
    parser.add_argument("file", type=Path, help="Path to SafeLang source")
    parser.add_argument(
        "--version",
        action="version",
        version=f"safelang {__version__}",
    )
    parser.add_argument("--nasm", type=Path, help="Write NASM output to file")
    parser.add_argument(
        "--clock-mhz",
        type=float,
        default=DEFAULT_CLOCK_HZ / 1_000_000,
        help="Target clock in MHz used to convert cycle estimates to ns",
    )
    parser.add_argument(
        "--no-time-check",
        action="store_true",
        help="Skip the worst-case execution time check against @time budgets",
    )
    parser.add_argument(
        "--time-report",
        action="store_true",
        help="Print the WCET estimate for every function",
    )
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

    if args.clock_mhz <= 0:
        print("ERROR: --clock-mhz must be positive", file=sys.stderr)
        return 1
    clock_hz = int(args.clock_mhz * 1_000_000)

    if not errors and not args.no_time_check:
        errors.extend(check_time_budgets(funcs, clock_hz))

    if not errors and args.time_report:
        reports, _ = analyze(funcs, clock_hz)
        for report in reports:
            print(report.describe())

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    try:
        if args.nasm:
            asm = compile_to_nasm(funcs)
            try:
                args.nasm.write_text(asm)
            except OSError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
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
