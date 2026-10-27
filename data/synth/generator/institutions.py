"""Generate ~300 synthetic institutions using Faker en_IN.

All data is synthetic. PLACEHOLDER: All handbook values left unfilled.
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from faker import Faker

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Chandigarh", "Puducherry",
]

INSTITUTION_TYPES = [
    "Technical Institute", "Engineering College", "Polytechnic",
    "College of Engineering", "Institute of Technology",
    "School of Engineering", "Technical University",
]

TRUST_TYPES = [
    "Education Trust", "Educational Society", "Charitable Trust",
    "Educational Foundation", "Welfare Trust",
]


def generate_institutions(n: int = 300, seed: int = 42) -> list[dict]:
    """Generate n synthetic institutions."""
    Faker.seed(seed)
    random.seed(seed)
    institutions = []

    for i in range(n):
        state = random.choice(STATES)
        city = fake.city()
        name_base = fake.last_name()
        inst_type = random.choice(INSTITUTION_TYPES)
        trust_type = random.choice(TRUST_TYPES)

        inst = {
            "name": f"{name_base} {inst_type}",
            "code": f"SYNTH-{i+1:04d}",
            "address": fake.street_address(),
            "city": city,
            "state": state,
            "pin_code": fake.postcode(),
            "trust_name": f"{name_base} {trust_type}",
            "trust_registration_number": f"TR/{state[:2].upper()}/{random.randint(1000,9999)}/{random.randint(2000,2024)}",
            "is_canary": False,
        }
        institutions.append(inst)

    return institutions


def generate_canary_institutions(n: int = 30, seed: int = 99) -> list[dict]:
    """Generate n canary institutions (for monitoring, not visible to API)."""
    Faker.seed(seed)
    random.seed(seed)
    canaries = []

    for i in range(n):
        state = random.choice(STATES)
        inst = {
            "name": f"Canary Institute {i+1:03d}",
            "code": f"CANARY-{i+1:04d}",
            "address": fake.street_address(),
            "city": fake.city(),
            "state": state,
            "pin_code": fake.postcode(),
            "trust_name": f"Canary Trust {i+1:03d}",
            "trust_registration_number": f"TR/CAN/{random.randint(1000,9999)}/{random.randint(2000,2024)}",
            "is_canary": True,
        }
        canaries.append(inst)

    return canaries


def save_institutions(institutions: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(institutions, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(institutions)} institutions to {path}")


def insert_institutions(institutions: list[dict], db_name: str = "aicte_validator"):
    """Insert institutions into the database."""
    import psycopg2
    conn = psycopg2.connect(dbname=db_name, host="/tmp")
    cur = conn.cursor()

    for inst in institutions:
        cur.execute(
            "INSERT INTO institutions (name, code, address, city, state, pin_code, is_canary) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (code) DO NOTHING",
            (inst["name"], inst["code"], inst["address"], inst["city"],
             inst["state"], inst["pin_code"], inst["is_canary"])
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {len(institutions)} institutions into database")


if __name__ == "__main__":
    out_dir = Path("data/synth/generator")

    print("Generating institutions...")
    institutions = generate_institutions(300)
    save_institutions(institutions, out_dir / "institutions.json")
    insert_institutions(institutions)

    print("Generating canary institutions...")
    canaries = generate_canary_institutions(30)
    save_institutions(canaries, out_dir / "canary_institutions.json")
    insert_institutions(canaries)

    print(f"✅ Total: {len(institutions) + len(canaries)} institutions")
