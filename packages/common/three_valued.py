"""Three-valued logic for the AICTE rules engine.

Kleene logic: TRUE, FALSE, UNKNOWN.
UNKNOWN never produces a rejection or a mismatch.
"""
from __future__ import annotations

from enum import Enum
from typing import Iterable


class Ternary(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    def __bool__(self) -> bool:
        raise TypeError(
            "Ternary values must not be used in boolean context. "
            "Use explicit comparison: result == Ternary.TRUE"
        )

    @staticmethod
    def all_of(items: Iterable[Ternary]) -> Ternary:
        """Kleene AND: FALSE if any FALSE, else UNKNOWN if any UNKNOWN, else TRUE."""
        has_unknown = False
        for item in items:
            if item == Ternary.FALSE:
                return Ternary.FALSE
            if item == Ternary.UNKNOWN:
                has_unknown = True
        return Ternary.UNKNOWN if has_unknown else Ternary.TRUE

    @staticmethod
    def any_of(items: Iterable[Ternary]) -> Ternary:
        """Kleene OR: TRUE if any TRUE, else UNKNOWN if any UNKNOWN, else FALSE."""
        has_unknown = False
        for item in items:
            if item == Ternary.TRUE:
                return Ternary.TRUE
            if item == Ternary.UNKNOWN:
                has_unknown = True
        return Ternary.UNKNOWN if has_unknown else Ternary.FALSE

    @staticmethod
    def not_(value: Ternary) -> Ternary:
        """Kleene NOT: swaps TRUE and FALSE, UNKNOWN stays."""
        if value == Ternary.TRUE:
            return Ternary.FALSE
        if value == Ternary.FALSE:
            return Ternary.TRUE
        return Ternary.UNKNOWN


def may_reject(result: Ternary) -> bool:
    """UNKNOWN and TRUE never produce a rejection. Only FALSE may."""
    if result == Ternary.UNKNOWN:
        return False
    return result == Ternary.FALSE


ThreeValued = Ternary
