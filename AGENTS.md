# ARGUS agent rules

Project: AI governance platform (FastAPI, Postgres+pgvector, React, Claude API).
Python project and docker-compose.yml are in the nested `argus/` folder.

## Environment
- Windows PowerShell 5.x: do not chain commands with &&.
- Docker Desktop works. The backend image uses CPU-only torch; keep it that way
  (never let CUDA/nvidia packages into requirements).
- Run docker commands from the `argus/` folder.

## Rules
- Never use, print, or write a real API key. `.env` must never be committed.
- Keep changes minimal. No refactors unless asked.
- Do NOT commit or push. When done, show `git status --short`.
- If a build runs over 15 minutes or shows repeated network retries, stop and report.
- Report only what you actually ran. Mark anything not run as UNVERIFIED.
- Do not tune thresholds or edit data to force a demo result.

## Status
- Works with no API key (SQLite fallback): registry, fairness/drift monitor,
  both demos (scripts/run_bias_demo.py, scripts/run_drift_demo.py), 4 pytest tests.
- Docker stack builds. RAG ingestion loads the EU AI Act PDF (144 pages, 277
  chunks) but fails with: PGVector.__init__() got an unexpected keyword
  argument 'connection_string'.
- Not yet verified: real RAG retrieval, Claude-powered agents, dashboard in
  browser, audit PDF via API.
  