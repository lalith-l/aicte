# AICTE Validation Prototype

**Everything runs on synthetic data. This is a demonstration prototype only.**

## Quick Start

### 1. Install Dependencies

```bash
# PostgreSQL 16 + pgvector
brew install postgresql@16 pgvector
brew services start postgresql@16
createdb aicte_validator

# System dependencies for PDF/OCR
brew install poppler tesseract tesseract-lang ffmpeg

# Python dependencies
cd /Users/lalithkumargn/Desktop/aicte
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Frontend dependencies
cd web
npm install
```

### 2. Set Up Database

```bash
source .venv/bin/activate
python scripts/setup_db.py
python scripts/seed_demo.py
```

### 3. Run the Application

**Terminal 1 - Backend:**
```bash
source .venv/bin/activate
cd services/api
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd web
npm run dev
```

### 4. Access the Demo

1. Open http://localhost:5173
2. Click quick login: **Scrutiny Officer** (officer_raj)
3. Navigate to Sunrise Technical Institute application
4. Explore findings with PLACEHOLDER clause references
5. Open **Demo Drawer** (right side) to toggle chaos mode

## Demo Users (password: demo123)

- `officer_raj` — Scrutiny Officer
- `supervisor_priya` — Supervisor
- `auditor_amit` — Auditor
- `rules_meera` — Rules Admin
- `sunrise_admin` — Institution User (Sunrise Institute)
- `sysadmin_dev` — System Admin

## Architecture

- **Backend**: FastAPI + PostgreSQL 16 + pgvector
- **Frontend**: React 19 + TypeScript + Vite
- **Sandbox**: macOS sandbox-exec (deny-list profile)
- **Auth**: PyJWT + argon2id
- **Vision**: CPU-only (DINOv2 + OWLv2) inside sandbox

## Ground Rules

1. **Authority Rule**: Only deterministic code can write findings
2. **Three-Valued Logic**: TRUE, FALSE, UNKNOWN
3. **Models Never Write Statuses**: Database roles enforce this
4. **UNKNOWN ≠ FALSE**: Uncertain evidence never causes rejection
5. **Placeholder Gates**: No rule can be approved with `clause_ref = "PLACEHOLDER"`
6. **All Data is Synthetic**: Never use for real decisions

## Key Files

- `CLAUDE.md` — Agent ground rules
- `aicte_build_plan.md` — Complete 17-day build plan
- `BUILD_STATUS.md` — Current completion status
- `scripts/setup_db.py` — Database schema with RLS + roles
- `scripts/seed_demo.py` — Sunrise Institute seed data
- `packages/common/three_valued.py` — Kleene logic
- `packages/rules/engine.py` — Three-valued rules engine
- `services/sandbox/sandbox_runner.py` — macOS sandbox
- `services/api/app/main.py` — FastAPI entry point
- `web/src/App.tsx` — React entry point

## Tests

```bash
pytest tests/unit/ -v
```

Must pass before Phase 1:
- `test_three_valued.py` — Kleene logic property tests
- `test_authority_rule.py` — Role enforcement
- `test_rls.py` — Row-level security
- `test_sandbox.py` — Sandbox isolation

## License

Prototype code for demonstration. All data is synthetic.
