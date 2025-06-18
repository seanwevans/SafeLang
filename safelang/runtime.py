"""SafeLang runtime helpers for saturating arithmetic.

If a value exceeds the representable range during clamping, a
``SaturatingOverflow`` error is raised. Callers are expected to catch this
exception to handle overflow conditions explicitly.
"""

from typing import Tuple


class SaturatingOverflow(Exception):
    """Raised when a value would exceed the representable range."""


def bounds(bits: int, signed: bool) -> Tuple[int, int]:
    if signed:
        max_val = 2 ** (bits - 1) - 1
        min_val = -2 ** (bits - 1)
    else:
        max_val = 2 ** bits - 1
        min_val = 0
    return min_val, max_val


def clamp(value: int, bits: int, signed: bool) -> int:
    """Clamp ``value`` to the representable range.

    Raises ``SaturatingOverflow`` if the value is outside the range.
    """
    min_val, max_val = bounds(bits, signed)
    if value > max_val or value < min_val:
        raise SaturatingOverflow(
            f"value {value} outside [{min_val}, {max_val}]"
        )
    return value


def sat_add(a: int, b: int, bits: int, signed: bool = True) -> int:
    total = int(a) + int(b)
    return clamp(total, bits, signed)


def sat_sub(a: int, b: int, bits: int, signed: bool = True) -> int:
    total = int(a) - int(b)
    return clamp(total, bits, signed)


def sat_mul(a: int, b: int, bits: int, signed: bool = True) -> int:
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
