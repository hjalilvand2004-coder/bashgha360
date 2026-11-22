"""Money/points math — Decimal only, single rounding rule (PNT-04, ASM-02).

Rule: quantize to 2 decimals with ROUND_HALF_UP. Never float.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

Q2 = Decimal("0.01")
ZERO = Decimal("0.00")


def D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    return Decimal(str(value))


def round2(value) -> Decimal:
    return D(value).quantize(Q2, rounding=ROUND_HALF_UP)


def add(a, b) -> Decimal:
    return round2(D(a) + D(b))


def sub(a, b) -> Decimal:
    return round2(D(a) - D(b))


def mul(a, b) -> Decimal:
    """Product of two quantized factors — intermediate keeps full precision, result quantized."""
    return round2(D(a) * D(b))


def clamp_min_zero(v) -> Decimal:
    d = D(v)
    return d if d > ZERO else ZERO


ROUNDING_NAME = "ROUND_HALF_UP@2dp"
