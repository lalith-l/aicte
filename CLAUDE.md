# Agent Ground Rules

These rules bind every agent session working on this codebase.

## Authority Rule
Only deterministic code (rules, record comparison, signature and source checks) and humans
can write a status or a finding. Models write only indicators and scores. This is enforced
with database roles (`app_det` for findings, `app_model` for indicators), not convention.

## Three-Valued Logic
Every check returns `TRUE`, `FALSE`, or `UNKNOWN`. `UNKNOWN` never produces a rejection
or a mismatch.

## Models Never Write Statuses
No model output has authority over a finding or document_status. The database role `app_model`
physically cannot INSERT into `findings`, `document_status`, or `verification_results`.

## Run Tests Before Claiming Done
Run the test suite before claiming any task is complete.

## Never Edit a Test to Make It Pass
Fix the code, not the test.

## Sandbox Has No Network
The document-parsing sandbox denies all network access via `sandbox-exec`.

## No Secrets in Code
Secrets live in files under `secrets/` or environment variables. Never commit them.
`secrets/` is in `.gitignore`.

## Never Invent Handbook Clause Numbers
Clause references (`clause_ref`) must come from the real AICTE Approval Process Handbook,
filled by a person. Rules with placeholder clause references cannot be approved or activated.

## Synthetic Data
Everything runs on synthetic data. Label it on every screen and report.

## Apple Silicon
This runs on Apple Silicon (M1). Use CPU for vision inside the sandbox. MPS only outside.
