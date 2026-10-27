"""WeasyPrint document templates — generate synthetic PDFs.

Each template produces a realistic-looking PDF for one document type.
All data is synthetic. PLACEHOLDER: No real clause references, handbook
numbers, or minimum values are generated.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import qrcode
from io import BytesIO
import base64


def _qr_base64(data: str) -> str:
    """Generate a QR code as base64 PNG."""
    qr = qrcode.make(data, box_size=4, border=2)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: 'Noto Sans', Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 16pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 6pt; margin-bottom: 12pt; }
h2 { font-size: 13pt; color: #2a4a6c; margin-top: 14pt; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0; }
th, td { border: 1px solid #ccc; padding: 6pt 8pt; text-align: left; font-size: 10pt; }
th { background: #e8eef5; font-weight: 600; }
.header { text-align: center; margin-bottom: 20pt; }
.header h1 { border: none; }
.seal { text-align: center; margin-top: 24pt; font-style: italic; color: #666; }
.signature { margin-top: 40pt; display: flex; justify-content: space-between; }
.sig-block { text-align: center; border-top: 1px solid #333; padding-top: 4pt; min-width: 200px; }
.synthetic-label { background: #fff3cd; border: 1px solid #ffc107; padding: 4pt 8pt; text-align: center; font-size: 9pt; color: #856404; margin-bottom: 12pt; }
.qr { text-align: right; margin-top: 12pt; }
.field-row { display: flex; gap: 20pt; margin-bottom: 4pt; }
.field-label { font-weight: 600; min-width: 180px; }
.footer { margin-top: 24pt; border-top: 1px solid #ccc; padding-top: 8pt; font-size: 9pt; color: #888; text-align: center; }
"""


def _trust_deed_html(inst: dict) -> str:
    qr = _qr_base64(f"TRUST:{inst['code']}|REG:{inst.get('trust_registration_number','N/A')}")
    return f"""<html><head><style>{CSS}</style></head><body>
    <div class="synthetic-label">⚠ SYNTHETIC DOCUMENT — NOT FOR OFFICIAL USE</div>
    <div class="header"><h1>TRUST DEED</h1>
    <p>Registration Number: {inst.get('trust_registration_number', 'N/A')}</p></div>
    <h2>1. Parties</h2>
    <div class="field-row"><span class="field-label">Trust Name:</span><span>{inst.get('trust_name', inst['name'] + ' Trust')}</span></div>
    <div class="field-row"><span class="field-label">Institution Name:</span><span>{inst['name']}</span></div>
    <div class="field-row"><span class="field-label">Address:</span><span>{inst['address']}, {inst['city']}, {inst['state']} - {inst['pin_code']}</span></div>
    <h2>2. Purpose</h2>
    <p>The Trust is established for the sole purpose of promoting technical education in accordance with AICTE regulations.</p>
    <p>Clause Reference: <strong>PLACEHOLDER</strong> (to be filled from handbook)</p>
    <h2>3. Properties and Assets</h2>
    <table><tr><th>Asset Type</th><th>Description</th><th>Value (₹)</th></tr>
    <tr><td>Land</td><td>{random.randint(2,20)} acres at {inst['city']}</td><td>{random.randint(50,500) * 100000:,}</td></tr>
    <tr><td>Building</td><td>Main campus building</td><td>{random.randint(100,800) * 100000:,}</td></tr>
    <tr><td>Equipment</td><td>Laboratory and teaching aids</td><td>{random.randint(10,100) * 100000:,}</td></tr></table>
    <h2>4. Governance</h2>
    <p>The Trust shall be governed by a Board of Trustees consisting of not less than PLACEHOLDER members.</p>
    <div class="qr"><img src="data:image/png;base64,{qr}" /></div>
    <div class="seal">— This deed is executed on {datetime.now().strftime('%d %B %Y')} —</div>
    <div class="footer">Generated for AICTE Validation Prototype — All data is synthetic</div>
    </body></html>"""


def _affidavit_html(inst: dict, signatory: str, pan: str, date: str) -> str:
    return f"""<html><head><style>{CSS}</style></head><body>
    <div class="synthetic-label">⚠ SYNTHETIC DOCUMENT — NOT FOR OFFICIAL USE</div>
    <div class="header"><h1>AFFIDAVIT</h1>
    <p>On Stamp Paper of ₹{random.choice([100,200,500])}</p></div>
    <p>I, <strong>{signatory}</strong>, PAN: <strong>{pan}</strong>, acting as the authorized signatory
    of <strong>{inst['name']}</strong>, do hereby solemnly affirm and declare the following:</p>
    <ol>
    <li>That all information provided in the application for AICTE approval for the academic year is true and correct to the best of my knowledge.</li>
    <li>That the institution complies with all AICTE norms as specified in Clause <strong>PLACEHOLDER</strong> of the Approval Process Handbook.</li>
    <li>That the institution has the minimum required infrastructure as per PLACEHOLDER.</li>
    <li>That the faculty-to-student ratio meets the requirement of PLACEHOLDER.</li>
    <li>That the fee structure is as approved by the fee regulatory authority.</li>
    </ol>
    <p>Date: <strong>{date}</strong></p>
    <p>Place: <strong>{inst['city']}, {inst['state']}</strong></p>
    <div style="margin-top:60pt; text-align:right;">
    <div class="sig-block">{signatory}<br/>Authorized Signatory</div>
    </div>
    <div class="footer">Generated for AICTE Validation Prototype — All data is synthetic</div>
    </body></html>"""


def _faculty_list_html(inst: dict, count: int) -> str:
    from faker import Faker
    fake = Faker("en_IN")
    rows = ""
    designations = ["Professor", "Associate Professor", "Assistant Professor", "Lecturer"]
    departments = ["CSE", "ECE", "ME", "CE", "EEE", "IT", "MBA", "MCA"]
    for i in range(count):
        rows += f"<tr><td>{i+1}</td><td>{fake.name()}</td><td>{random.choice(designations)}</td>"
        rows += f"<td>{random.choice(departments)}</td><td>{fake.bothify('??######?')}</td>"
        rows += f"<td>{random.choice(['PhD','M.Tech','M.E.','MBA','MCA'])}</td></tr>\n"

    return f"""<html><head><style>{CSS}</style></head><body>
    <div class="synthetic-label">⚠ SYNTHETIC DOCUMENT — NOT FOR OFFICIAL USE</div>
    <div class="header"><h1>Faculty List — {inst['name']}</h1></div>
    <p>Total Faculty: <strong>{count}</strong> | Required per PLACEHOLDER: <strong>PLACEHOLDER</strong></p>
    <table><tr><th>#</th><th>Name</th><th>Designation</th><th>Department</th><th>ID</th><th>Qualification</th></tr>
    {rows}</table>
    <div class="footer">Generated for AICTE Validation Prototype — All data is synthetic</div>
    </body></html>"""


def _noc_html(inst: dict, issuer: str, noc_date: str) -> str:
    qr = _qr_base64(f"NOC:{inst['code']}|DATE:{noc_date}")
    return f"""<html><head><style>{CSS}</style></head><body>
    <div class="synthetic-label">⚠ SYNTHETIC DOCUMENT — NOT FOR OFFICIAL USE</div>
    <div class="header"><h1>No Objection Certificate</h1>
    <p>{issuer}</p></div>
    <p>This is to certify that <strong>{inst['name']}</strong>, located at {inst['address']}, {inst['city']},
    {inst['state']} - {inst['pin_code']}, has been granted a No Objection Certificate for the purpose of
    seeking AICTE approval for the academic year.</p>
    <p>Reference: PLACEHOLDER</p>
    <p>Date of Issue: <strong>{noc_date}</strong></p>
    <p>Valid Until: <strong>PLACEHOLDER</strong></p>
    <div class="qr"><img src="data:image/png;base64,{qr}" /></div>
    <div style="margin-top:40pt;"><div class="sig-block">Authorized Officer<br/>{issuer}</div></div>
    <div class="footer">Generated for AICTE Validation Prototype — All data is synthetic</div>
    </body></html>"""


def _generic_html(inst: dict, doc_type: str) -> str:
    title_map = {
        "stamp_paper": "Stamp Paper Certificate",
        "land_documents": "Land Ownership Certificate",
        "building_plan": "Building Plan Approval",
        "fee_structure": "Fee Structure Declaration",
        "bank_statement": "Bank Statement Summary",
        "fire_safety_certificate": "Fire Safety Certificate",
    }
    title = title_map.get(doc_type, doc_type.replace("_", " ").title())
    return f"""<html><head><style>{CSS}</style></head><body>
    <div class="synthetic-label">⚠ SYNTHETIC DOCUMENT — NOT FOR OFFICIAL USE</div>
    <div class="header"><h1>{title}</h1></div>
    <p>Institution: <strong>{inst['name']}</strong></p>
    <p>Code: <strong>{inst['code']}</strong></p>
    <p>Location: {inst['city']}, {inst['state']}</p>
    <p>Date: {datetime.now().strftime('%d %B %Y')}</p>
    <p>This document is issued in compliance with AICTE requirements. Clause reference: <strong>PLACEHOLDER</strong>.</p>
    <p>Minimum requirements: <strong>PLACEHOLDER</strong> (refer to handbook).</p>
    <div class="footer">Generated for AICTE Validation Prototype — All data is synthetic</div>
    </body></html>"""


TEMPLATE_MAP = {
    "trust_deed": lambda inst, **kw: _trust_deed_html(inst),
    "affidavit": lambda inst, **kw: _affidavit_html(inst, kw.get("signatory", "Dr. A. Kumar"),
                                                     kw.get("pan", "ABCPK1234Z"),
                                                     kw.get("date", "2025-01-15")),
    "faculty_list": lambda inst, **kw: _faculty_list_html(inst, kw.get("count", 42)),
    "noc": lambda inst, **kw: _noc_html(inst, kw.get("issuer", "State Government"),
                                         kw.get("noc_date", "2025-02-10")),
}


def render_pdf(html: str, output_path: Path) -> Path:
    """Render HTML to PDF using WeasyPrint."""
    from weasyprint import HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path))
    return output_path


def generate_document_pdf(inst: dict, doc_type: str, output_dir: Path, **kwargs) -> Path:
    """Generate a single PDF for a document type."""
    template_fn = TEMPLATE_MAP.get(doc_type, lambda inst, **kw: _generic_html(inst, doc_type))
    html = template_fn(inst, **kwargs)
    out = output_dir / f"{doc_type}.pdf"
    return render_pdf(html, out)
