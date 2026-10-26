import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

modules = [
    "health",
    "auth.routes",
    "applications",
    "documents",
    "findings",
    "verification",
    "reports",
    "review_queue",
    "alerts",
    "audit_routes",
    "rules_routes",
    "system_routes",
    "portal_routes",
    "jobs",
    "demo",
]

for mod in modules:
    t0 = time.time()
    try:
        if mod.startswith("auth."):
            __import__("services.api.app." + mod)
        else:
            __import__("services.api.app.routes." + mod)
        dt = time.time() - t0
        print(f"OK: {mod} ({dt:.2f}s)")
    except Exception as e:
        print(f"FAIL: {mod} -> {e}")
