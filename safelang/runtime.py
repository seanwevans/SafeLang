"""SafeLang runtime helpers for saturating arithmetic.

All helpers return both the clamped result and a boolean indicating whether
the operation saturated. Overflow never raises an exception; callers must
check the returned flag to determine if clamping occurred.
"""

from typing import Tuple


def bounds(bits: int, signed: bool) -> Tuple[int, int]:
    if bits <= 0:
        raise ValueError("bits must be positive")

    if signed:
        max_val = 2 ** (bits - 1) - 1
        min_val = -2 ** (bits - 1)
    else:
        max_val = 2 ** bits - 1
        min_val = 0
    return min_val, max_val


def clamp(value: int, bits: int, signed: bool) -> Tuple[int, bool]:
    """Clamp ``value`` to the representable range.

    Returns a tuple of the clamped value and a boolean indicating whether
    saturation occurred.
    """
    min_val, max_val = bounds(bits, signed)
    if value > max_val:
        return max_val, True
    if value < min_val:
        return min_val, True
    return value, False


def sat_add(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Add ``a`` and ``b`` with saturating semantics."""
    total = int(a) + int(b)
    return clamp(total, bits, signed)


def sat_sub(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Subtract ``b`` from ``a`` with saturating semantics."""
    total = int(a) - int(b)
    return clamp(total, bits, signed)


def sat_mul(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Multiply ``a`` and ``b`` with saturating semantics."""
    total = int(a) * int(b)
    return clamp(total, bits, signed)


def sat_div(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Divide ``a`` by ``b`` with saturating semantics."""
    bounds(bits, signed)  # validate bit width
    if int(b) == 0:
        raise ZeroDivisionError("division by zero")
    total = int(a) // int(b)
    return clamp(total, bits, signed)


def sat_mod(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Compute ``a`` modulo ``b`` with saturating semantics."""
    bounds(bits, signed)  # validate bit width
    if int(b) == 0:
        raise ZeroDivisionError("integer modulo by zero")
    total = int(a) % int(b)
    return clamp(total, bits, signed)


__all__ = [
    "bounds",
    "clamp",
    "sat_add",
    "sat_sub",
    "sat_mul",
    "sat_div",
    "sat_mod",
]
