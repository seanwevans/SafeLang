"""Minimal demo runtime for the SafeLang compiler."""

from .runtime import sat_add, sat_sub, sat_mul, sat_div, sat_mod
from .parser import FunctionDef, parse_functions, verify_contracts
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
    "generate_c",
]
