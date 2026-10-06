# Docker stack and dashboard readiness ? 2026-10-06

Stack left RUNNING. Started with docker compose up -d, no --build. No prompts, thresholds or retrieval changed. No commits.

## Seed and monitoring

PostgreSQL connection confirmed; 574 EU AI Act embeddings. New API system UUIDs match the PostgreSQL rows, ruling out SQLite for these registrations. Exactly one registration each, EU only, version dashboard-2026-10-06.

| System | ID | Tier | Snapshots | Alerts |
|---|---|---|---|---|
| credit_scoring | credit_scoring_model-4dbb0f | HIGH_RISK | 1 | 2 |
| fraud_detector | fraud_detection_engi-2a6271 | MINIMAL_RISK | 1 | 3 |
| spam_filter | email_spam_filter-c64b88 | MINIMAL_RISK | 0 | 0 |

Estimated 6 live calls; actual 5, one cache hit, zero errors/429s. Gemini gemini-3.5-flash-lite; 23,398 input and 1,762 output tokens from SDK metadata. The backend was restarted only to load PDF fixes; no further LLM calls followed.

Bias demo: approval rates under_30=0.109589, 30_plus=0.357616; demographic parity difference=0.248027, equalized odds difference=0.329183; two CRITICAL alerts. Drift demo: PSI V1=0.893621, V3=1.019934, V14=0.828686, overall=0.132430; three drift alerts. Existing artifacts used unchanged. Both scripts executed inside backend against http://localhost:8000.

## Audit PDF via curl

Corrected record ID: 8d570a87-6ad7-43e9-afc2-5269b6ee30e4. Measured POST elapsed: 1.204046 seconds. Downloaded size: 7394 bytes, 4 pages.

Stored SHA-256: `a80614bf0017fd364b9774e9e5b7709e59c8cb65485b6d64afe8c92e85e943eb`

Recomputed downloaded SHA-256: `a80614bf0017fd364b9774e9e5b7709e59c8cb65485b6d64afe8c92e85e943eb`

Hashes match. Original pre-fix audit: 0.474246 seconds, 6,923 bytes; it remains available as evidence.

Sections extracted from the downloaded corrected PDF: Executive Summary; 1. System Overview; 2. Risk Classification; 3. Fairness & Drift Monitoring History; 4. Governance Alerts; 5. Open Remediation Tasks; 6. Audit Trail & Metadata.

PDF COMPLIANT/CRITICAL obligation mismatches: none observed. There are zero occurrences of COMPLIANT and no per-obligation status assessment at all. The PDF lists the two CRITICAL fairness alerts and required Article 10 data/bias monitoring obligation. Absence of COMPLIANT labels does not mean obligations were verified. The separate compliance endpoint returns score 50, checks_passed=8 and checks_failed=2; these are synthetic counters, not an obligation-by-obligation assessment.

## Dashboard pages and API contracts

Built bundle API URL: http://localhost:8000; effective base URL: http://localhost:8000/api/v1. Dashboard and all checked page routes returned HTTP 200. CORS POST preflight returned 200 and each explicit Origin for http://localhost:3000 and http://localhost:5173; simple GET returns allow-origin=*; current Axios client does not request cross-origin credentials.

| Page | Calls | Fields consumed / expected shape |
|---|---|---|
| / Dashboard | GET /registry/systems; GET /monitoring/alerts | arrays; system_id, name, risk_tier, owner_team; alerts length |
| /registry Registry | GET /registry/systems | array; system_id, name, risk_tier, owner_team, jurisdictions:string[] |
| /monitoring Monitoring | GET /monitoring/alerts | array; id, title, severity, resolved:boolean |
| /audit Audit | POST /audit/generate-dossier | object; pdf_path:string |
| /systems/:systemId System Detail | GET /registry/systems/:systemId; GET /audit/records?system_id=...; GET /audit/records/:id/download | object: name, purpose, risk_tier, owner_team, regulatory_citations; records array with id; PDF blob |
| * Not Found | none | no API dependency |

Every unique page endpoint was called using curl.exe (POST and download included); all expected fields and checked field types matched. No dashboard/API field mismatch found. Detailed actual response fields:

- GET /api/v1/registry/systems: array; fields jurisdictions, monitoring_enabled, name, owner_team, registered_at, risk_tier, system_id; missing fields [].
- GET /api/v1/registry/systems/credit_scoring_model-4dbb0f: object; fields affected_demographics, data_sources, id, jurisdictions, last_classified_at, llm_model, llm_provider, model_card, model_type, monitoring_enabled, name, needs_review, needs_review_reasons, output_type, owner_email, owner_team, purpose, registered_at, regulatory_citations, risk_classification_reasoning, risk_tier, status, system_id, version; missing fields [].
- GET /api/v1/monitoring/alerts: array; fields alert_type, created_at, description, id, payload, regulatory_references, resolved, resolved_at, severity, system_id, title; missing fields [].
- GET /api/v1/audit/records?system_id=credit_scoring_model-4dbb0f: array; fields compliance_summary, content_hash, generated_at, generated_by, id, pdf_path, system_id; missing fields [].
- POST /api/v1/audit/generate-dossier: object; fields compliance_summary, content_hash, generated_at, generated_by, id, pdf_path, system_id; missing fields [].
- GET /api/v1/audit/records/8d570a87-6ad7-43e9-afc2-5269b6ee30e4/download: application/pdf binary; fields PDF blob; missing fields [].

## Real bugs fixed

- weasyprint.py local ReportLab fallback drew unwrapped lines beyond the right edge; now wraps to printable width. Regression verifies all words are present and their visible bounds fit the page.
- Audit template labelled a source HTML digest as Content Hash; now explicitly labels Source HTML Hash (SHA-256, before hash insertion). The API/database content_hash remains the actual PDF digest.
- PDF citation table displayed raw Article/Annex field alone, losing paragraph/point. It now uses canonical_citation with raw article fallback; Annex III point 5(b) verified in downloaded text.

Changed files: weasyprint.py, argus/core/agents/audit_generator.py, tests/test_audit_generator.py. Copied into backend with docker compose cp and restarted backend; no rebuild performed.

Container pytest -q: 95 passed (5 warnings). After strengthening the visible-bounds regression, targeted audit tests: 2 passed (3 warnings).

## UNVERIFIED and limits

- Browser rendering, click interactions, and browser-managed PDF download are UNVERIFIED; no browser used. HTTP, built URL, response fields/types, CORS headers, and downloaded PDF text verified.
- Per-obligation regulatory compliance and alert-to-obligation mapping are not computed by the PDF. No regulatory compliance conclusion is claimed.
- The local ReportLab shim remains the renderer; full WeasyPrint HTML/CSS layout is not used.
- Fixes are active in the existing container, not baked into an image; future container recreation needs copying them again or a build.

Artifacts: dashboard_seed_20261006.json, dashboard_http_checks_20261006.json, audit_http_check_20261006.json, audit_http_fixed_check_20261006.json, audit_pdf_analysis_20261006.json, credit_audit_20261006.pdf, credit_audit_fixed_20261006.pdf, credit_audit_fixed_20261006.txt. Earlier measurement fixtures/reports were not edited.
