"""Application generator: dev/calibration/test/canary splits with Must-tier defects."""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from packages.synth.defects import finding_reason, pick_defects
from packages.synth.templates import DOC_TYPES, html_for, render_pdf

SPLITS = {
    "dev": (400, 101),
    "calibration": (600, 202),
    "test": (400, 303),
    "canary": (300, 404),
}


def generate_applications(institutions: list[dict], split: str, dest_dir) -> list[dict[str, Any]]:
    n, seed = SPLITS[split]
    dest_dir.mkdir(parents=True, exist_ok=True)
    apps = []
    categories = ["eoa_renewal", "new_approval", "intake_enhancement"]
    for i in range(n):
        inst = institutions[i % len(institutions)]
        app_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{split}-{i}-{inst['code']}"))
        defects = pick_defects(i, split)
        fields = {
            "institution_name": inst["name"],
            "code": inst["code"],
            "academic_year": "2025-26",
            "pan": "AAACT1234A" if i % 17 else "INVALIDPAN",
            "affidavit_date": "2025-01-15",
            "stamp_paper_date": "2024-12-01" if any(d["code"] == "D04" for d in defects) else "2025-01-10",
            "qr": "TRUST:SYNTHETIC",
        }
        docs = []
        for t in DOC_TYPES[:5]:
            html = html_for(t, fields)
            pdf_path = dest_dir / f"{app_id[:8]}_{t}.pdf"
            render_pdf(html, pdf_path)
            sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            docs.append({"type": t, "path": str(pdf_path), "sha256": sha, "pages": 1})
        apps.append(
            {
                "id": app_id,
                "institution_id": inst["id"],
                "declared_category": categories[i % 3],
                "academic_year": "2025-26",
                "split": split,
                "defects": defects,
                "documents": docs,
                "findings": [
                    {
                        "source_code": d["code"],
                        "tier": d["tier"],
                        "result": d["result"],
                        "reason": finding_reason(d["code"]),
                        "clause_ref": "PLACEHOLDER",
                    }
                    for d in defects
                    if d["code"] != "D21"
                ],
                "synthetic": True,
            }
        )
    return apps
