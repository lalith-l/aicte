# Procfile for honcho (run all services)
# Install honcho: pip install honcho
# Run: honcho start

api: cd services/api && uvicorn app.main:app --reload --port 8000
worker: python services/worker/worker.py
mock_portal: uvicorn services.mock_portal.portal:app --port 8001
mock_issuers: uvicorn services.mock_issuers.issuer_server:app --port 8002
