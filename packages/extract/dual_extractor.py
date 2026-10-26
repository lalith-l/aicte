"""Dual extraction engine.

Extracts structured fields using dual independent methods:
1. Born-digital extractor (PyMuPDF / pdfplumber layout & text)
2. Scanned / OCR extractor (Pytesseract / image-based text)

Agreement Logic:
- If both extractors agree on normalized value: confidence = HIGH, agree = True
- If extractors disagree or low confidence: agree = False, value flagged,
  evaluates to UNKNOWN under Three-Valued Kleene logic.
  Crucial AICTE rule: UNKNOWN never triggers an automatic rejection.

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional
from difflib import SequenceMatcher

from packages.common.three_valued import ThreeValued


@dataclass
class ExtractedField:
    field_name: str
    value: Any
    confidence: float
    agree: bool
    extractor_primary: str
    extractor_secondary: str
    primary_value: Any
    secondary_value: Any
    bbox: Optional[list[float]] = None
    page: int = 1
    three_valued_status: ThreeValued = ThreeValued.TRUE
    clause_ref_placeholder: str = "PLACEHOLDER"


def _clean_text(val: str) -> str:
    if not val:
        return ""
    return re.sub(r"\s+", " ", str(val)).strip().lower()


def _fuzzy_match(val1: str, val2: str, threshold: float = 0.85) -> bool:
    clean1 = _clean_text(val1)
    clean2 = _clean_text(val2)
    if not clean1 or not clean2:
        return False
    if clean1 == clean2:
        return True
    return SequenceMatcher(None, clean1, clean2).ratio() >= threshold


class DualExtractor:
    """Orchestrates dual extraction and agreement checking."""

    PATTERNS = {
        "pan_number": r"[A-Z]{5}[0-9]{4}[A-Z]",
        "date": r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})\b",
        "acres": r"(\d+(?:\.\d+)?)\s*(?:acres|acre|hectares|sq\.?\s*m)",
        "currency": r"₹?\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)",
    }

    @staticmethod
    def extract_fields_from_text(text: str, doc_type: str) -> dict[str, Any]:
        """Extract candidate key-value pairs from text."""
        fields = {}
        if not text:
            return fields

        # Extract PAN
        pans = re.findall(DualExtractor.PATTERNS["pan_number"], text)
        if pans:
            fields["pan_number"] = pans[0]

        # Extract dates
        dates = re.findall(DualExtractor.PATTERNS["date"], text)
        if dates:
            fields["document_date"] = dates[0]

        # Look for institution name
        inst_match = re.search(r"(?:Institution Name|Name of Institution)[:\s]+([^\n\r]+)", text, re.IGNORECASE)
        if inst_match:
            fields["institution_name"] = inst_match.group(1).strip()

        # Look for trust name
        trust_match = re.search(r"(?:Trust Name|Name of Trust)[:\s]+([^\n\r]+)", text, re.IGNORECASE)
        if trust_match:
            fields["trust_name"] = trust_match.group(1).strip()

        # Look for land area
        land_match = re.search(DualExtractor.PATTERNS["acres"], text, re.IGNORECASE)
        if land_match:
            fields["land_area_acres"] = land_match.group(1)

        return fields

    @classmethod
    def compare_and_reconcile(
        cls,
        primary_fields: dict[str, Any],
        secondary_fields: dict[str, Any],
        bdigital: bool = True,
    ) -> list[ExtractedField]:
        """Reconcile fields between the two extraction pipelines."""
        all_keys = set(primary_fields.keys()).union(secondary_fields.keys())
        results = []

        for key in sorted(all_keys):
            p_val = primary_fields.get(key)
            s_val = secondary_fields.get(key)

            if p_val is not None and s_val is not None:
                # Check agreement
                if isinstance(p_val, str) and isinstance(s_val, str):
                    agree = _fuzzy_match(p_val, s_val)
                else:
                    agree = (p_val == s_val)

                confidence = 0.95 if agree else 0.50
                three_status = ThreeValued.TRUE if agree else ThreeValued.UNKNOWN
                chosen_value = p_val if agree or bdigital else s_val
            elif p_val is not None:
                agree = False
                confidence = 0.70
                three_status = ThreeValued.UNKNOWN  # Not corroborated -> UNKNOWN
                chosen_value = p_val
            else:
                agree = False
                confidence = 0.60
                three_status = ThreeValued.UNKNOWN
                chosen_value = s_val

            results.append(
                ExtractedField(
                    field_name=key,
                    value=chosen_value,
                    confidence=confidence,
                    agree=agree,
                    extractor_primary="PyMuPDF" if bdigital else "LayoutEngine",
                    extractor_secondary="PytesseractOCR",
                    primary_value=p_val,
                    secondary_value=s_val,
                    three_valued_status=three_status,
                )
            )

        return results
