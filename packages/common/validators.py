"""Deterministic identifier / date validators shared by the generator, extraction
and the rules engine. Pure functions, no I/O.

Honest scope note
-----------------
* GSTIN carries a real mod-36 check character (the GST algorithm) -> a true *checksum*.
* PAN has NO checksum; only structure (5 letters, 4 digits, 1 letter, 4th letter =
  holder type). We validate structure and say so rather than pretending otherwise.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
# 4th character = holder type (P individual, C company, T trust, F firm, A AOP, B BOI,
# G govt, H HUF, L local authority, J artificial juridical person)
PAN_HOLDER_TYPES = set("PCTFABGHLJ")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def validate_pan(value: Optional[str]) -> bool:
    if not value:
        return False
    v = value.strip().upper()
    return bool(PAN_RE.match(v)) and v[3] in PAN_HOLDER_TYPES


def gstin_check_char(first14: str) -> str:
    """GST mod-36 check character over the first 14 characters."""
    total = 0
    for i, ch in enumerate(first14):
        code = _GST_CHARS.index(ch)
        factor = 1 if i % 2 == 0 else 2
        prod = code * factor
        total += prod // 36 + prod % 36
    return _GST_CHARS[(36 - (total % 36)) % 36]


def validate_gstin(value: Optional[str]) -> bool:
    if not value:
        return False
    v = value.strip().upper()
    if not GSTIN_RE.match(v):
        return False
    return gstin_check_char(v[:14]) == v[14]


def make_gstin(state_code: int, pan: str, entity: int = 1) -> str:
    base = f"{state_code:02d}{pan}{entity}Z"
    return base + gstin_check_char(base)


def mask_identifier(value: Optional[str], keep: int = 4) -> str:
    """Mask all but the last `keep` characters (PAN/GSTIN display)."""
    if not value:
        return ""
    v = str(value)
    if len(v) <= keep:
        return "•" * len(v)
    return "•" * (len(v) - keep) + v[-keep:]


_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y", "%B %d, %Y")


def parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_name(value: Optional[str]) -> str:
    """Case/punctuation/'&'-insensitive name normal form for comparison."""
    if not value:
        return ""
    s = value.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(the|of)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()
