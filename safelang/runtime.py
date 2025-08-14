"""SafeLang runtime helpers for saturating arithmetic.

All helpers return both the clamped result and a boolean indicating whether
the operation saturated. Overflow never raises an exception; callers must
check the returned flag to determine if clamping occurred.
"""

from typing import Tuple


def bounds(bits: int, signed: bool) -> Tuple[int, int]:
    """Return the minimum and maximum representable values for ``bits``.

    ``signed`` selects between two's complement and unsigned ranges. ``bits``
    must be between 1 and 63 inclusive to match the C runtime limits.
    """
    if bits <= 0:
        raise ValueError("bits must be positive")
    if bits > 63:
        raise ValueError("bits must be 63 or less")

    if signed:
        max_val = 2 ** (bits - 1) - 1
        min_val = -(2 ** (bits - 1))
    else:
        max_val = 2**bits - 1
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
    """Add ``a`` and ``b`` with saturating semantics.

    Raises:
        ValueError: If ``signed`` is ``False`` and either operand is negative.
    """
    ia, ib = int(a), int(b)
    if not signed and (ia < 0 or ib < 0):
        raise ValueError("negative operands not allowed in unsigned mode")
    total = ia + ib
    return clamp(total, bits, signed)


def sat_sub(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Subtract ``b`` from ``a`` with saturating semantics.

    Raises:
        ValueError: If ``signed`` is ``False`` and either operand is negative.
    """
    ia, ib = int(a), int(b)
    if not signed and (ia < 0 or ib < 0):
        raise ValueError("negative operands not allowed in unsigned mode")
    total = ia - ib
    return clamp(total, bits, signed)


def sat_mul(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Multiply ``a`` and ``b`` with saturating semantics.

    Raises:
        ValueError: If ``signed`` is ``False`` and either operand is negative.
    """
    ia, ib = int(a), int(b)
    if not signed and (ia < 0 or ib < 0):
        raise ValueError("negative operands not allowed in unsigned mode")
    total = ia * ib
    return clamp(total, bits, signed)


def sat_div(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Divide ``a`` by ``b`` with saturating semantics.

    Raises:
        ZeroDivisionError: If ``b`` is zero.
        ValueError: If ``signed`` is ``False`` and either operand is negative.
    """
    bounds(bits, signed)  # validate bit width

    ia, ib = int(a), int(b)
    if ib == 0:
        raise ZeroDivisionError("division by zero")
    if not signed and (ia < 0 or ib < 0):
        raise ValueError("negative operands not allowed in unsigned mode")

    abs_a = abs(ia)
    abs_b = abs(ib)
    quotient = abs_a // abs_b
    if (ia < 0) ^ (ib < 0):
        quotient = -quotient
    return clamp(quotient, bits, signed)


def sat_mod(a: int, b: int, bits: int, signed: bool = True) -> Tuple[int, bool]:
    """Compute ``a`` modulo ``b`` with saturating semantics.

    Raises:
        ZeroDivisionError: If ``b`` is zero.
        ValueError: If ``signed`` is ``False`` and either operand is negative.
    """
    bounds(bits, signed)  # validate bit width
    ia, ib = int(a), int(b)
    if ib == 0:
        raise ZeroDivisionError("integer modulo by zero")
    if not signed and (ia < 0 or ib < 0):
        raise ValueError("negative operands not allowed in unsigned mode")

    abs_a = abs(ia)
    abs_b = abs(ib)
    quotient = abs_a // abs_b
    if (ia < 0) ^ (ib < 0):
        quotient = -quotient
    remainder = ia - quotient * ib
    return clamp(remainder, bits, signed)


__all__ = [
    "bounds",
    "clamp",
    "sat_add",
    "sat_sub",
    "sat_mul",
    "sat_div",
    "sat_mod",
]
