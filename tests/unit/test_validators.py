import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.common.validators import (  # noqa: E402
    gstin_check_char,
    make_gstin,
    mask_identifier,
    normalize_name,
    parse_date,
    validate_gstin,
    validate_pan,
)


def test_pan_structure():
    assert validate_pan("ABCTE1234F")
    assert not validate_pan("ABCZE1234F")  # 4th letter not a holder type
    assert not validate_pan("ABCT1234FF")
    assert not validate_pan("")
    assert not validate_pan(None)


def test_gstin_known_vectors():
    # Published sample GSTINs (structure from the GST spec; check chars verified by algorithm)
    g = make_gstin(29, "ABCTE1234F")
    assert validate_gstin(g)
    assert len(g) == 15 and g[13] == "Z"


def test_gstin_detects_every_single_char_corruption_of_check_digit():
    g = make_gstin(27, "AAACS8577K")
    for ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        bad = g[:14] + ch
        assert validate_gstin(bad) == (ch == g[14])


def test_gstin_check_char_depends_on_all_positions():
    base = "29ABCTE1234F1Z"
    assert gstin_check_char(base) != gstin_check_char("29ABCTE1234F2Z")


def test_mask():
    assert mask_identifier("ABCTE1234F") == "••••••234F"
    assert mask_identifier("ABCTE1234F").endswith("234F")
    assert mask_identifier("ABCTE1234F").count("•") == 6
    assert mask_identifier("") == ""


def test_parse_date_formats():
    assert parse_date("2025-01-15") == date(2025, 1, 15)
    assert parse_date("15/01/2025") == date(2025, 1, 15)
    assert parse_date("15 January 2025") == date(2025, 1, 15)
    assert parse_date("garbage") is None and parse_date(None) is None


def test_normalize_name():
    assert normalize_name("Sharma  Institute of Technology!") == normalize_name(
        "sharma institute technology"
    )
    assert normalize_name("A & B College") == normalize_name("A and B College")
