"""WeasyPrint HTML+CSS templates for ~10 synthetic document types."""
from __future__ import annotations

from typing import Any

DOC_TYPES = [
    "trust_deed",
    "affidavit",
    "stamp_paper",
    "faculty_list",
    "noc",
    "land_record",
    "fire_noc",
    "fdr",
    "building_plan",
    "affiliation",
]


def html_for(doc_type: str, fields: dict[str, Any]) -> str:
    rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in fields.items())
    qr = fields.get("qr", "TRUST:SYNTHETIC")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"/>
<style>
  body {{ font-family: DejaVu Sans, sans-serif; margin: 32px; color: #111; }}
  h1 {{ font-size: 18px; border-bottom: 2px solid #1e3a8a; padding-bottom: 8px; }}
  .banner {{ background: #f59e0b; color: #111; padding: 6px 10px; font-weight: 700; font-size: 11px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }}
  .qr {{ margin-top: 24px; font-family: monospace; font-size: 11px; }}
  .sig {{ margin-top: 40px; border-top: 1px solid #999; width: 240px; padding-top: 6px; font-size: 11px; }}
</style></head>
<body>
  <div class="banner">SYNTHETIC DOCUMENT — NOT A REAL LEGAL INSTRUMENT</div>
  <h1>AICTE Prototype · {doc_type.replace('_', ' ').title()}</h1>
  <table>{rows}</table>
  <div class="qr">QR payload: {qr}</div>
  <div class="sig">Authorised signatory (synthetic)</div>
</body></html>
"""


def render_pdf(html: str, dest) -> bool:
    try:
        from weasyprint import HTML

        HTML(string=html).write_pdf(str(dest))
        return True
    except Exception:
        dest.write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
        )
        return False
