"""Minimal demo runtime for the SafeLang compiler."""

from .runtime import sat_add, sat_sub, sat_mul, sat_div, sat_mod
from .parser import FunctionDef, parse_functions, verify_contracts

from .compiler import generate_c, generate_rust
from .compiler import compile_to_nasm
from .compiler import generate_c

__all__ = [
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
