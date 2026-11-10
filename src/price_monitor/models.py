"""Shared domain models."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductObservation:
    url: str
    title: str
    price: Decimal
    currency: str | None
