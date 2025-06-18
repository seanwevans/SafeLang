"""SafeLang runtime helpers for saturating arithmetic.
"""

from typing import Tuple


class SaturatingOverflow(Exception):
    """Raised when saturation occurs."""


def bounds(bits: int, signed: bool) -> Tuple[int, int]:
    if signed:
        max_val = 2 ** (bits - 1) - 1
        min_val = -2 ** (bits - 1)
    else:
        max_val = 2 ** bits - 1
        min_val = 0
    return min_val, max_val


def clamp(value: int, bits: int, signed: bool) -> Tuple[int, bool]:
    """Clamp value to the representable range.

    Returns the clamped value and whether it saturated.
    """
    min_val, max_val = bounds(bits, signed)
    if value > max_val:
        return max_val, True
    if value < min_val:
        return min_val, True
    return value, False


def sat_add(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    total = int(a) + int(b)
    return clamp(total, bits, signed)


def sat_sub(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    total = int(a) - int(b)
    return clamp(total, bits, signed)


def sat_mul(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    total = int(a) * int(b)
    return clamp(total, bits, signed)


__all__ = [
    "SaturatingOverflow",
    "bounds",
    "clamp",
    "sat_add",
    "sat_sub",
    "sat_mul",
]
