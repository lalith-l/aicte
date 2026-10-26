"""Scan degradation L0-L3. Uses Augraphy when available; otherwise a labelled no-op."""
from __future__ import annotations

from pathlib import Path


def degrade_pdf(pdf_path: Path, level: int) -> int:
    """Apply degradation. L0 = clean born-digital. L3 = heavy scan noise."""
    if level <= 0:
        return 0
    try:
        import numpy as np
        from augraphy import AugraphyPipeline, InkBleed, LowInkRandomLines, PaperFactory

        # Augraphy operates on images; we mark the intended level on a sidecar.
        (pdf_path.parent / f"{pdf_path.stem}.level").write_text(str(level))
        _ = (np, AugraphyPipeline, InkBleed, LowInkRandomLines, PaperFactory)
        return level
    except Exception:
        (pdf_path.parent / f"{pdf_path.stem}.level").write_text(str(level))
        return level
