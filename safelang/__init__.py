"""Minimal demo runtime for the SafeLang compiler."""

__version__ = "0.1.0"

from .runtime import sat_add, sat_sub, sat_mul, sat_div, sat_mod
from .parser import FunctionDef, parse_functions, verify_contracts

from .compiler import compile_to_nasm, generate_c, generate_rust

__all__ = [
    "__version__",
    "sat_add",
    "sat_sub",
    "sat_mul",
    "sat_div",
    "sat_mod",
    "FunctionDef",
    "parse_functions",
    "verify_contracts",
    "compile_to_nasm",
    "generate_c",
    "generate_rust",
]
