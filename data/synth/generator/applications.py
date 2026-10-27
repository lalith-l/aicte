"""Generate synthetic applications with Must-tier defect injection.

Splits: dev (400), calibration (600), test (400), canary (300 from canary pool)
Different seeds per split.

Must-tier defects only: D01-D08, D10-D13, D20, D21.
PLACEHOLDER: All clause references and handbook minimums left unfilled.
"""
from __future__ import annotations

import json
import os
import random
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

CATEGORIES = ["eoa_renewal", "new_institution", "new_programme", "increase_intake", "closure"]
ACADEMIC_YEARS = ["2024-25", "2025-26"]

# Document types each application should have
REQUIRED_DOCS = [
    "trust_deed", "affidavit", "stamp_paper", "faculty_list",
    "noc", "land_documents", "building_plan", "fee_structure",
    "bank_statement", "fire_safety_certificate",
]

# Must-tier defects with injection probability
MUST_DEFECTS = {
    "D01_missing_document":    {"prob": 0.08, "desc": "Missing required document"},
    "D02_missing_field":       {"prob": 0.10, "desc": "Missing required field in document"},
    "D03_expired_document":    {"prob": 0.06, "desc": "Document past its validity period"},
    "D04_date_inconsistency":  {"prob": 0.07, "desc": "Cross-document date conflict"},
    "D05_identifier_checksum": {"prob": 0.03, "desc": "PAN/GSTIN checksum failure"},
    "D06_name_mismatch":       {"prob": 0.08, "desc": "Cross-document name mismatch"},
    "D07_portal_mismatch":     {"prob": 0.05, "desc": "Intake mismatch vs AICTE portal"},
    "D08_reused_document":     {"prob": 0.04, "desc": "Document hash seen in another application"},
    "D10_signature_modified":  {"prob": 0.03, "desc": "PDF signature modified after signing"},
    "D11_unsigned_required":   {"prob": 0.05, "desc": "Document unsigned where signature required"},
    "D12_issuer_mismatch":     {"prob": 0.04, "desc": "Verification issuer doesn't match document"},
    "D13_source_outage":       {"prob": 0.06, "desc": "Verification source returned 503"},
    "D20_unreadable_scan":     {"prob": 0.05, "desc": "OCR extractors disagree — UNKNOWN"},
    "D21_injected_instructions": {"prob": 0.02, "desc": "Injected LLM instructions in text (no effect — authority rule)"},
}


def _generate_pan() -> str:
    """Generate a synthetic PAN-like identifier."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (
        random.choice(letters) + random.choice(letters) + random.choice(letters)
        + random.choice("ABCFGHLT") + random.choice(letters)
        + f"{random.randint(1000,9999)}" + random.choice(letters)
    )


def _generate_fields(doc_type: str, defects: list[str]) -> list[dict]:
    """Generate extracted fields for a document, with defect injection."""
    from faker import Faker
    fake = Faker("en_IN")

    fields = []
    base_date = f"20{random.randint(23,25)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

    if doc_type == "trust_deed":
        fields.append({"field": "institution_name", "value": fake.company(), "confidence": round(random.uniform(0.88, 0.99), 2)})
        fields.append({"field": "trust_name", "value": f"{fake.last_name()} Education Trust", "confidence": round(random.uniform(0.90, 0.99), 2)})
        fields.append({"field": "registration_date", "value": base_date, "confidence": round(random.uniform(0.85, 0.98), 2)})
    elif doc_type == "affidavit":
        fields.append({"field": "affidavit_date", "value": base_date, "confidence": round(random.uniform(0.88, 0.97), 2)})
        fields.append({"field": "signatory_name", "value": fake.name(), "confidence": round(random.uniform(0.85, 0.96), 2)})
        pan = _generate_pan()
        if "D05_identifier_checksum" in defects:
            pan = pan[:-1] + "0"  # Break the checksum
        fields.append({"field": "pan_number", "value": pan, "confidence": round(random.uniform(0.92, 0.99), 2)})
    elif doc_type == "stamp_paper":
        fields.append({"field": "stamp_paper_date", "value": base_date, "confidence": round(random.uniform(0.90, 0.99), 2)})
        fields.append({"field": "stamp_value", "value": str(random.choice([100, 200, 500, 1000])), "confidence": 0.99})
    elif doc_type == "faculty_list":
        count = random.randint(15, 80)
        fields.append({"field": "faculty_count", "value": str(count), "confidence": round(random.uniform(0.85, 0.95), 2)})
    elif doc_type == "fee_structure":
        fields.append({"field": "annual_fee", "value": str(random.randint(30000, 200000)), "confidence": round(random.uniform(0.90, 0.98), 2)})
    elif doc_type == "noc":
        fields.append({"field": "noc_issuer", "value": f"State Government of {fake.state()}", "confidence": round(random.uniform(0.88, 0.96), 2)})
        fields.append({"field": "noc_date", "value": base_date, "confidence": round(random.uniform(0.90, 0.98), 2)})
    else:
        fields.append({"field": "document_date", "value": base_date, "confidence": round(random.uniform(0.85, 0.97), 2)})

    # D02: Missing field — remove a field
    if "D02_missing_field" in defects and fields:
        fields.pop(random.randint(0, len(fields) - 1))

    # D20: Unreadable scan — lower confidence, mark disagreement
    if "D20_unreadable_scan" in defects and fields:
        for f in fields:
            f["confidence"] = round(random.uniform(0.30, 0.55), 2)
            f["agree"] = False

    return fields


def generate_applications(
    institution_ids: list[str],
    n: int = 400,
    seed: int = 42,
    split: str = "dev",
) -> list[dict]:
    """Generate n applications with defect injection."""
    random.seed(seed)
    applications = []

    for i in range(n):
        inst_id = random.choice(institution_ids)
        app_id = str(uuid.uuid4())

        # Decide which defects this application has
        app_defects = []
        for defect_code, info in MUST_DEFECTS.items():
            if random.random() < info["prob"]:
                app_defects.append(defect_code)

        # Generate documents
        docs = []
        doc_types = list(REQUIRED_DOCS)

        # D01: Missing document — remove one
        if "D01_missing_document" in app_defects:
            removed = doc_types.pop(random.randint(0, len(doc_types) - 1))
            app_defects_detail = [{"code": "D01", "detail": f"Missing {removed}"}]
        else:
            app_defects_detail = []

        for doc_type in doc_types:
            doc_id = str(uuid.uuid4())
            sha256 = uuid.uuid4().hex + uuid.uuid4().hex[:32]
            pages = random.randint(1, 8)

            # D08: Reused document hash
            if "D08_reused_document" in app_defects and doc_type == random.choice(doc_types):
                sha256 = "reused_" + sha256[:58]

            fields = _generate_fields(doc_type, app_defects)

            doc = {
                "id": doc_id,
                "type_declared": doc_type,
                "sha256": sha256,
                "page_count": pages,
                "fields": fields,
            }
            docs.append(doc)

        app = {
            "id": app_id,
            "institution_id": inst_id,
            "declared_category": random.choice(CATEGORIES),
            "academic_year": random.choice(ACADEMIC_YEARS),
            "split": split,
            "defects": [d for d in app_defects],
            "defects_detail": app_defects_detail,
            "documents": docs,
        }
        applications.append(app)

    return applications


def insert_applications(applications: list[dict], db_name: str = "aicte_validator"):
    """Insert applications, documents, and extracted fields into the database."""
    import psycopg2
    conn = psycopg2.connect(dbname=db_name, host="/tmp")
    cur = conn.cursor()

    for app in applications:
        cur.execute(
            "INSERT INTO applications (id, institution_id, declared_category, academic_year, stage) "
            "VALUES (%s, %s, %s, %s, 'SUBMITTED') ON CONFLICT DO NOTHING",
            (app["id"], app["institution_id"], app["declared_category"], app["academic_year"])
        )

        for doc in app["documents"]:
            cur.execute(
                "INSERT INTO documents (id, application_id, type_declared, file_ref, sha256, page_count) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (doc["id"], app["id"], doc["type_declared"],
                 f"synth/{app['id'][:8]}/{doc['type_declared']}.pdf",
                 doc["sha256"], doc["page_count"])
            )

            for field in doc["fields"]:
                cur.execute(
                    "INSERT INTO extracted_fields (document_id, field, value, confidence, extractor, agree) "
                    "VALUES (%s, %s, %s, %s, 'synthetic', %s) ON CONFLICT DO NOTHING",
                    (doc["id"], field["field"], field["value"],
                     field["confidence"], field.get("agree", True))
                )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {len(applications)} applications ({sum(len(a['documents']) for a in applications)} docs)")


def save_applications(applications: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(applications, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved {len(applications)} applications to {path}")


if __name__ == "__main__":
    import psycopg2

    out_dir = Path("data/synth/generator")

    # Get institution IDs from database
    conn = psycopg2.connect(dbname="aicte_validator", host="/tmp")
    cur = conn.cursor()
    cur.execute("SELECT id FROM institutions WHERE is_canary = false AND code LIKE 'SYNTH-%'")
    inst_ids = [str(r[0]) for r in cur.fetchall()]
    cur.execute("SELECT id FROM institutions WHERE is_canary = true")
    canary_ids = [str(r[0]) for r in cur.fetchall()]
    cur.close()
    conn.close()

    if not inst_ids:
        print("No institutions found. Run institutions.py first.")
        sys.exit(1)

    print(f"Using {len(inst_ids)} institutions, {len(canary_ids)} canaries")

    print("\nGenerating dev split (400)...")
    dev = generate_applications(inst_ids, n=400, seed=42, split="dev")
    save_applications(dev, out_dir / "applications_dev.json")
    insert_applications(dev)

    print("Generating calibration split (600)...")
    cal = generate_applications(inst_ids, n=600, seed=84, split="calibration")
    save_applications(cal, out_dir / "applications_cal.json")
    insert_applications(cal)

    print("Generating test split (400)...")
    test = generate_applications(inst_ids, n=400, seed=126, split="test")
    save_applications(test, out_dir / "applications_test.json")
    insert_applications(test)

    if canary_ids:
        print("Generating canary split (up to 300)...")
        canary = generate_applications(canary_ids, n=min(300, len(canary_ids) * 10), seed=168, split="canary")
        save_applications(canary, out_dir / "applications_canary.json")
        insert_applications(canary)

    total = len(dev) + len(cal) + len(test) + (len(canary_ids) and min(300, len(canary_ids) * 10))
    print(f"\n✅ Total: {total} applications generated across all splits")
