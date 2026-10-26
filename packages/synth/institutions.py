"""~300 synthetic Indian institutions via Faker en_IN."""
from __future__ import annotations

import random
import uuid
from typing import Any

STATES = [
    ("Karnataka", "Bengaluru"),
    ("Tamil Nadu", "Chennai"),
    ("Maharashtra", "Pune"),
    ("Telangana", "Hyderabad"),
    ("Gujarat", "Ahmedabad"),
    ("Rajasthan", "Jaipur"),
    ("West Bengal", "Kolkata"),
    ("Odisha", "Bhubaneswar"),
    ("Kerala", "Thiruvananthapuram"),
    ("Uttar Pradesh", "Lucknow"),
    ("Delhi", "New Delhi"),
    ("Punjab", "Chandigarh"),
]


def generate_institutions(n: int = 300, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    try:
        from faker import Faker

        fake = Faker("en_IN")
        fake.seed_instance(seed)
    except Exception:
        fake = None
    out = []
    used = set()
    for i in range(n):
        state, city = STATES[i % len(STATES)]
        name = (
            fake.company() + " Institute of Technology"
            if fake
            else f"Synthetic Institute {i:03d}"
        )
        code = f"SYN-{i:04d}"
        while code in used:
            code = f"SYN-{rng.randint(0, 9999):04d}"
        used.add(code)
        out.append(
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, code)),
                "name": name,
                "code": code,
                "address": fake.address().replace("\n", ", ") if fake else f"{i} Academic Road",
                "city": city,
                "state": state,
                "pin_code": f"{rng.randint(100000, 999999)}",
                "synthetic": True,
            }
        )
    return out
