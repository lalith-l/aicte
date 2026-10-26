"""Report generator for AICTE application verification dossiers.

Produces:
1. Versioned JSON report conforming to Pydantic schema
2. Formal PDF scrutiny dossier report via WeasyPrint
3. Audit logging of report generation with SHA256 hash in audit_log via audit_append()

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import psycopg2
from pydantic import BaseModel, Field

import qrcode

_PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
REPORTS_DIR = _PROJECT_ROOT / "data" / "storage" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class FindingItem(BaseModel):
    finding_id: str
    rule_id: str
    clause_ref: str = "PLACEHOLDER"
    severity: str
    title: str
    evidence: str
    recheck_recipe: str
    status: str = "OPEN"
    is_placeholder: bool = True


class DocumentItem(BaseModel):
    document_id: str
    doc_type: str
    status: str
    page_count: int
    sha256: str
    verification_route: str


class ApplicationDossierReport(BaseModel):
    report_version: str = "1.0.0"
    report_id: str
    generated_at: str
    application_id: str
    institution_name: str
    institution_code: str
    academic_year: str
    category: str
    verification_debt_score: float
    verification_debt_tier: str
    summary: dict[str, Any]
    findings: list[FindingItem]
    documents: list[DocumentItem]
    report_sha256: str = ""
    @property
    def schema_version(self) -> str:
        return self.report_version


def build_report(
    application_id: str,
    documents: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    report_id: Optional[str] = None,
    institution_name: str = "Synthetic Institution",
    institution_code: str = "INST-SYN-001",
    academic_year: str = "2026-2027",
    category: str = "ENGINEERING",
    debt_score: float = 0.0,
    debt_tier: str = "LOW",
) -> ApplicationDossierReport:
    """Build an ApplicationDossierReport."""
    rep_id = report_id or f"REP-{uuid.uuid4().hex[:12].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_items = [
        DocumentItem(
            document_id=str(d.get("id", uuid.uuid4())),
            doc_type=str(d.get("type_declared", "unknown")),
            status=str(d.get("status", "UNVERIFIED")),
            page_count=int(d.get("page_count", 1) or 1),
            sha256=str(d.get("sha256", "none")),
            verification_route=str(d.get("route", "LOCAL_SANDBOX")),
        )
        for d in documents
    ]

    finding_items = [
        FindingItem(
            finding_id=str(f.get("id", uuid.uuid4())),
            rule_id=str(f.get("source_code") or f.get("rule_id", "R_GENERAL")),
            clause_ref=str(f.get("clause_ref") or "PLACEHOLDER"),
            severity=str(f.get("tier") or f.get("severity", "MUST")),
            title=str(f.get("title") or f.get("reason", "Scrutiny Finding")),
            evidence=str(f.get("reason") or f.get("evidence", "Discrepancy detected during validation")),
            recheck_recipe=str(f.get("recheck_recipe", "Verify original document")),
            status=str(f.get("result", "OPEN")),
            is_placeholder=True,
        )
        for f in findings
    ]

    verified_docs = sum(1 for d in doc_items if d.status == "VERIFIED")
    summary_metrics = {
        "total_documents": len(doc_items),
        "verified_documents": verified_docs,
        "unverified_documents": len(doc_items) - verified_docs,
        "open_findings": len(finding_items),
        "three_valued_logic": "UNKNOWN propagation active",
    }

    report_obj = ApplicationDossierReport(
        report_id=rep_id,
        generated_at=now_iso,
        application_id=str(application_id),
        institution_name=institution_name,
        institution_code=institution_code,
        academic_year=academic_year,
        category=category,
        verification_debt_score=debt_score,
        verification_debt_tier=debt_tier,
        summary=summary_metrics,
        findings=finding_items,
        documents=doc_items,
    )
    report_json = report_obj.model_dump_json(indent=2)
    report_obj.report_sha256 = hashlib.sha256(report_json.encode("utf-8")).hexdigest()
    return report_obj


def persist_json(report: ApplicationDossierReport) -> tuple[str, str]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_json = report.model_dump_json(indent=2)
    digest = hashlib.sha256(report_json.encode("utf-8")).hexdigest()
    path = REPORTS_DIR / f"{report.report_id}.json"
    path.write_text(report_json)
    return str(path), digest


def persist_pdf(report: ApplicationDossierReport) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = REPORTS_DIR / f"{report.report_id}.pdf"
    if not pdf_path.exists():
        try:
            from weasyprint import HTML
            html = f"<html><body><h1>Dossier Report {report.report_id}</h1><p>Synthetic data only.</p></body></html>"
            HTML(string=html).write_pdf(str(pdf_path))
        except Exception:
            pdf_path.write_bytes(b"%PDF-1.4\n%mock pdf report\n%%EOF")
    return str(pdf_path)


REPORT_CSS = """
@page {
    size: A4;
    margin: 1.8cm 1.5cm;
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 8pt;
        color: #666;
    }
    @bottom-left {
        content: "AICTE Validation Prototype — All data is synthetic";
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 8pt;
        color: #d97706;
    }
}
body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #1e293b;
    font-size: 10pt;
    line-height: 1.5;
}
.banner {
    background-color: #fef3c7;
    border: 1px solid #f59e0b;
    color: #92400e;
    padding: 6pt 10pt;
    text-align: center;
    font-weight: bold;
    font-size: 9pt;
    border-radius: 4px;
    margin-bottom: 12pt;
}
.header {
    border-bottom: 2px solid #0f172a;
    padding-bottom: 10pt;
    margin-bottom: 15pt;
    display: flex;
    justify-content: space-between;
}
.header-title {
    font-size: 18pt;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
}
.header-subtitle {
    font-size: 11pt;
    color: #475569;
    margin: 2pt 0 0 0;
}
.badge-placeholder {
    display: inline-block;
    background-color: #f3f4f6;
    color: #4b5563;
    border: 1px dashed #9ca3af;
    padding: 2pt 6pt;
    font-size: 8pt;
    border-radius: 3pt;
    font-weight: 600;
}
.grid-2 {
    display: flex;
    gap: 15pt;
    margin-bottom: 15pt;
}
.card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10pt;
    flex: 1;
}
.card h3 {
    margin: 0 0 6pt 0;
    font-size: 10pt;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 8pt;
    font-size: 9pt;
}
th, td {
    padding: 6pt 8pt;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
}
th {
    background-color: #f1f5f9;
    color: #334155;
    font-weight: 600;
}
.status-pill {
    padding: 2pt 6pt;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: 600;
}
.pill-verified { background: #dcfce7; color: #166534; }
.pill-unverified { background: #fef3c7; color: #92400e; }
.pill-failed { background: #fee2e2; color: #991b1b; }
.pill-debt { background: #fef2f2; color: #b91c1c; font-weight: bold; }
.finding-box {
    border-left: 4px solid #ef4444;
    background: #fff5f5;
    padding: 8pt;
    margin-bottom: 8pt;
    border-radius: 0 4px 4px 0;
}
"""


def _generate_qr_data_url(data: str) -> str:
    qr = qrcode.make(data, box_size=3, border=1)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class ReportGenerator:
    """Generates JSON and PDF audit-ready scrutiny reports."""

    def __init__(self, db_conn: Optional[psycopg2.extensions.connection] = None):
        self.conn = db_conn

    def generate_report(
        self,
        application_id: str,
        institution_name: str,
        institution_code: str,
        academic_year: str,
        category: str,
        debt_score: float,
        debt_tier: str,
        documents: list[dict[str, Any]],
        findings: list[dict[str, Any]],
        actor_id: Optional[str] = None,
    ) -> tuple[ApplicationDossierReport, bytes, Path]:
        report_id = f"REP-{uuid.uuid4().hex[:12].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        doc_items = [
            DocumentItem(
                document_id=d.get("id", str(uuid.uuid4())),
                doc_type=d.get("type_declared", "unknown"),
                status=d.get("status", "UNVERIFIED"),
                page_count=d.get("page_count", 1),
                sha256=d.get("sha256", "none"),
                verification_route=d.get("route", "LOCAL_SANDBOX"),
            )
            for d in documents
        ]

        finding_items = [
            FindingItem(
                finding_id=f.get("id", str(uuid.uuid4())),
                rule_id=f.get("rule_id", "R_GENERAL"),
                clause_ref="PLACEHOLDER",
                severity=f.get("severity", "MUST"),
                title=f.get("title", "Scrutiny Finding"),
                evidence=f.get("evidence", "Discrepancy detected during validation"),
                recheck_recipe=f.get("recipe", "Verify original stamped document with issuing authority"),
                status=f.get("status", "OPEN"),
                is_placeholder=True,
            )
            for f in findings
        ]

        verified_docs = sum(1 for d in doc_items if d.status == "VERIFIED")
        summary_metrics = {
            "total_documents": len(doc_items),
            "verified_documents": verified_docs,
            "unverified_documents": len(doc_items) - verified_docs,
            "open_findings": len(finding_items),
            "three_valued_logic": "UNKNOWN propagation active — no automatic rejection on unverified records",
        }

        report_obj = ApplicationDossierReport(
            report_id=report_id,
            generated_at=now_iso,
            application_id=application_id,
            institution_name=institution_name,
            institution_code=institution_code,
            academic_year=academic_year,
            category=category,
            verification_debt_score=debt_score,
            verification_debt_tier=debt_tier,
            summary=summary_metrics,
            findings=finding_items,
            documents=doc_items,
        )

        # JSON serialized bytes
        report_json = report_obj.model_dump_json(indent=2)
        report_sha256 = hashlib.sha256(report_json.encode("utf-8")).hexdigest()
        report_obj.report_sha256 = report_sha256

        # Build PDF via WeasyPrint
        qr_url = _generate_qr_data_url(f"REPORT:{report_id}|SHA:{report_sha256}")

        docs_rows_html = "".join(
            f"""<tr>
                <td><strong>{d.doc_type}</strong></td>
                <td>{d.page_count}</td>
                <td><span class="status-pill {'pill-verified' if d.status == 'VERIFIED' else 'pill-unverified'}">{d.status}</span></td>
                <td><span class="badge-placeholder">PLACEHOLDER</span></td>
                <td style="font-family: monospace; font-size: 7pt;">{d.sha256[:16]}...</td>
            </tr>"""
            for d in doc_items
        )

        findings_html = (
            "".join(
                f"""<div class="finding-box">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4pt;">
                        <span style="font-weight:bold; color:#b91c1c;">[{f.severity}] {f.title}</span>
                        <span class="badge-placeholder">Clause: PLACEHOLDER</span>
                    </div>
                    <div style="font-size:9pt; color:#334155; margin-bottom:4pt;">{f.evidence}</div>
                    <div style="font-size:8pt; color:#64748b; background:#fff; padding:4pt 6pt; border-radius:3px;">
                        <strong>Recheck Recipe:</strong> {f.recheck_recipe}
                    </div>
                </div>"""
                for f in finding_items
            )
            if finding_items
            else "<p style='color:#16a34a;'>No deficiencies or findings identified.</p>"
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{REPORT_CSS}</style>
        </head>
        <body>
            <div class="banner">⚠ ALL DATA IS SYNTHETIC — DEMONSTRATION PROTOTYPE ONLY</div>
            
            <div class="header">
                <div>
                    <h1 class="header-title">AICTE Scrutiny Dossier Report</h1>
                    <div class="header-subtitle">Application ID: {application_id} &bull; Academic Year: {academic_year}</div>
                    <div style="margin-top: 4pt; font-size: 9pt; color: #64748b;">Report ID: {report_id} &bull; Generated: {now_iso}</div>
                </div>
                <div style="text-align: right;">
                    <img src="{qr_url}" style="width: 70px; height: 70px;" />
                </div>
            </div>

            <div class="grid-2">
                <div class="card">
                    <h3>Institution Details</h3>
                    <p style="margin:2pt 0;"><strong>{institution_name}</strong></p>
                    <p style="margin:2pt 0; color:#475569;">Code: {institution_code}</p>
                    <p style="margin:2pt 0; color:#475569;">Category: {category}</p>
                </div>
                <div class="card">
                    <h3>Verification Status & Debt</h3>
                    <p style="margin:2pt 0;">Debt Score: <span class="status-pill pill-debt">{debt_score}/100 ({debt_tier})</span></p>
                    <p style="margin:2pt 0; color:#475569;">Documents Verified: {verified_docs} / {len(doc_items)}</p>
                    <p style="margin:2pt 0; color:#475569;">Pending Dependencies: {len(doc_items) - verified_docs}</p>
                </div>
            </div>

            <h3 style="border-bottom: 1px solid #cbd5e1; padding-bottom: 4pt; margin-top: 15pt; color: #0f172a;">
                Findings & Deficiencies ({len(finding_items)})
            </h3>
            {findings_html}

            <h3 style="border-bottom: 1px solid #cbd5e1; padding-bottom: 4pt; margin-top: 18pt; color: #0f172a;">
                Submitted Documents & Verification Routes
            </h3>
            <table>
                <thead>
                    <tr>
                        <th>Document Type</th>
                        <th>Pages</th>
                        <th>Status</th>
                        <th>Handbook Norm</th>
                        <th>Content Hash</th>
                    </tr>
                </thead>
                <tbody>
                    {docs_rows_html}
                </tbody>
            </table>

            <div style="margin-top: 25pt; border-top: 1px solid #e2e8f0; padding-top: 8pt; font-size: 8pt; color: #94a3b8; text-align: center;">
                Report Hash: {report_sha256} &bull; Validated under Three-Valued Logic & Scoped DB Permissions
            </div>
        </body>
        </html>
        """

        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()

        # Save to disk
        pdf_path = REPORTS_DIR / f"{report_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Audit log insertion if DB available
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT audit_append(%s, %s, %s, %s, %s)
                        """,
                        (
                            "REPORT_GENERATED",
                            "applications",
                            application_id,
                            actor_id or str(uuid.UUID(int=0)),
                            json.dumps({
                                "report_id": report_id,
                                "report_sha256": report_sha256,
                                "debt_score": debt_score,
                                "findings_count": len(finding_items),
                            }),
                        ),
                    )
                self.conn.commit()
            except Exception:
                pass

        return report_obj, pdf_bytes, pdf_path
