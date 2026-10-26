"""Generate synthetic institutions, applications, Must-tier defects, and PDFs.

Default is a small local set. Pass --full for the plan volumes
(300 institutions; 400/600/400/300 applications).

All data is synthetic.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.common.paths import PDF_DIR, SYNTH_DIR, ensure_dirs  # noqa: E402
from packages.synth.applications import SPLITS, generate_applications  # noqa: E402
from packages.synth.degrade import degrade_pdf  # noqa: E402
from packages.synth.institutions import generate_institutions  # noqa: E402
from packages.synth.signing import ensure_mock_ca, sign_pdf  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true", help="Plan-scale volumes (slow)")
    p.add_argument("--sign", action="store_true")
    p.add_argument("--degrade-level", type=int, default=0)
    args = p.parse_args()
    ensure_dirs()
    ensure_mock_ca()
    n_inst = 300 if args.full else 24
    institutions = generate_institutions(n_inst)
    (SYNTH_DIR / "institutions.json").write_text(json.dumps(institutions, indent=2))
    all_apps = []
    for split, (n, _) in SPLITS.items():
        count = n if args.full else min(8, n)
        # Temporarily shrink by slicing after generate would still build `n` PDFs.
        # So generate with a patched local loop:
        from packages.synth import applications as appmod

        original = appmod.SPLITS[split]
        appmod.SPLITS[split] = (count, original[1])
        apps = generate_applications(institutions, split, PDF_DIR / split)
        appmod.SPLITS[split] = original
        if args.sign or args.degrade_level:
            for a in apps:
                for d in a["documents"]:
                    from pathlib import Path

                    path = Path(d["path"])
                    if args.sign:
                        sign_pdf(path)
                    if args.degrade_level:
                        degrade_pdf(path, args.degrade_level)
        (SYNTH_DIR / f"applications_{split}.json").write_text(json.dumps(apps, indent=2))
        all_apps.extend(apps)
        print(f"{split}: {len(apps)} applications")
    print(f"total {len(all_apps)} synthetic applications under {SYNTH_DIR}")


if __name__ == "__main__":
    main()
