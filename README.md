# ARGUS: AI Governance & Risk Unified System

A self-hostable platform that keeps an inventory of AI systems, classifies them under the EU AI Act with citations retrieved from the Act's actual text, monitors them for fairness and input drift, and produces audit dossiers on demand. Built around the needs of regulated industries such as banking.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Portfolio%20project-orange.svg)]()

> **This is a portfolio project, not a compliance product.** Risk tiers are produced by a small LLM and are advisory. They need human review, and nothing here is legal advice. See [Known limitations](#known-limitations).

---

## The problem

Large financial institutions run many AI systems at once: credit scoring, fraud detection, document classification. Each one needs to be:

- **Inventoried**: owner, data sources, purpose
- **Risk-classified**: under the EU AI Act, some uses are prohibited, some are high-risk with mandatory obligations
- **Monitored**: for fairness gaps and input drift
- **Audit-ready**: evidence that can be produced when a regulator asks

ARGUS is a prototype of the tooling layer for that work.

---

## What it does

| Component | What it does | Validation status |
|---|---|---|
| **Registry** | Stores systems, metadata, classifications, alerts, snapshots, audit records in PostgreSQL | Used end to end |
| **Registrar agent** | Extracts metadata and drafts a model card from a submission | Ran live with Gemini |
| **Risk classifier** | Classifies a system under the EU AI Act using retrieved legal text, with grounded citations | Evaluated on 32 hand-labelled cases (below) |
| **Fairness and drift monitor** | Demographic parity, equalized odds, PSI per feature, tiered alerts | Unit tests plus two reproducible demos |
| **Regulatory propagation agent** | Reads a regulatory update, finds affected systems, creates remediation tasks | One live run with a synthetic update |
| **Audit generator** | Builds a PDF dossier (Jinja2 + WeasyPrint) and stores its SHA-256 | Used through the API and dashboard |
| **Governance Q&A** | Answers registry questions from SQL and regulation questions from retrieved text | 10-question check (below) |

---

## Architecture

```
                 React dashboard (localhost:3000)
                              |
                       FastAPI (localhost:8000)
   +--------------+-----------+-----------+----------------+
   | Registry     | Monitoring| Audit     | Q&A            |
   +------+-------+-----+-----+-----+-----+--------+-------+
          |             |           |              |
          v             v           v              v
   +---------------------------------------------------------+
   |  PostgreSQL + pgvector                                  |
   |  systems, alerts, snapshots, tasks, audit records,      |
   |  574 EU AI Act chunks (384-dim embeddings)              |
   +---------------------------------------------------------+
          ^
          |  retrieval (local embedding model, CPU)
   +------+---------------------+       +--------------------+
   | Risk classifier / Q&A      | ----> | LLM provider       |
   | retrieval + grounding check|       | (Gemini, hosted)   |
   +----------------------------+       +--------------------+
```

Everything except the LLM call runs locally in Docker. The embedding model (all-MiniLM-L6-v2) runs on CPU, so regulatory text is never sent out for indexing.

### How classification works

1. The submitted description is used to retrieve legal text from the indexed EU AI Act. Retrieval is deterministic: it uses only the user's description, never LLM-inferred fields.
2. Every classification context always includes **all of Article 5(1)** (the prohibited-practice screen), Article 6, Article 50, the best-matching Annex III chunk, and one extra top-scoring chunk. If the Article 5(1) screen is incomplete, no tier is returned (`context_incomplete`).
3. The LLM returns structured JSON, validated against a schema.
4. A **grounding check** keeps only citations whose own identity (article, annex, point) appears in the retrieved text. Unsupported citations are dropped.
5. Citations are canonicalised (for example "Article 5(1)(f)", "Annex III point 5(b)"). Provisions that were checked and excluded are stored separately and are not shown as supporting citations.
6. Deterministic review flags (`needs_review` plus reasons) cover low confidence, schema repair, dropped citations, missing retrieved context, and tier/citation inconsistencies.

The chunking is structure-aware: 574 chunks covering 113 articles and 13 annexes, split on Article/Annex headings and tagged with provision metadata, with every chunk prefixed by its heading. Text is extracted with PyMuPDF (pypdf split words and hurt retrieval).

### The LLM layer

One provider-agnostic layer (`argus/core/llm.py`) serves all agents:

- Provider chosen by `LLM_PROVIDER`; the model comes only from `GEMINI_MODEL` or `CLAUDE_MODEL` (startup check rejects display names such as "Gemini 3.5 Flash Lite"; use the API model ID)
- Response cache, per-process call cap, requests-per-minute throttle, bounded retries, usage log
- JSON schema validation with one repair attempt, then rule-based fallback
- Every output records `llm_provider` and `llm_model`

The Gemini path (`gemini-3.5-flash-lite`, free tier) is the one that has been run live. An Anthropic provider is implemented but **has not been validated live**.

---

## Tech stack

```
Backend:          Python 3.11, FastAPI, SQLAlchemy
LLM:              Gemini via google-genai (validated); Anthropic provider (not validated live)
Agents:           Standalone Python agents (no orchestration framework)
RAG:              PyMuPDF, sentence-transformers all-MiniLM-L6-v2, pgvector (langchain-postgres)
Database:         PostgreSQL 16 + pgvector
Fairness / drift: fairlearn, numpy/scipy (demographic parity, equalized odds, PSI)
PDF:              Jinja2 + WeasyPrint 62.3 (pydyf 0.10.0)
Frontend:         React 18 + TypeScript + Vite
Infra:            Docker Compose (CPU-only PyTorch; backend image about 3.8 GB)
Monitoring:       Prometheus metrics endpoint
Auth:             Development JWT stub (see limitations)
```

---

## Quickstart

### Prerequisites

- Docker Desktop (running)
- A Gemini API key from Google AI Studio (free tier is enough; without a key ARGUS runs in rule-based fallback mode)
- The EU AI Act PDF: Regulation (EU) 2024/1689, English, from EUR-Lex

### Run

```bash
git clone https://github.com/Akshatha-Gadasandula/ARGUS-AI-Governance-Risk-Unified-System.git
cd ARGUS-AI-Governance-Risk-Unified-System/argus
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=<API model ID from AI Studio, lowercase with hyphens>
LLM_MAX_CALLS=12
LLM_MAX_RPM=5
JWT_SECRET=<64 random hex characters>
```

Never commit `.env`. Then:

```bash
docker compose up -d --build
```

The first build is slow (several minutes of image export, much longer on a cold cache). The first classification downloads the embedding model (about 90 MB) into a Docker volume. After that it works offline.

- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs

### Index the EU AI Act

Place the PDF at `regulations/pdfs/eu_ai_act.pdf`, then:

```bash
docker compose exec backend python -m argus.rag.ingestion --source regulations/pdfs/eu_ai_act.pdf --framework EU_AI_ACT
```

Re-running replaces the collection, so it will not duplicate chunks. Expect 574 chunks.

RBI guidelines are not indexed. A system registered with jurisdiction `IN` shows RBI as `not_assessed_no_corpus`, with no tier and no LLM call.

### Register a system

```powershell
$body = @{ name = 'Credit Scoring Model v2'; purpose = 'Predicts probability of loan default using applicant transaction history'; data_sources = @('transaction_history','credit_bureau'); affected_demographics = @('age','income_band'); jurisdictions = @('EU'); owner_team = 'retail-credit-engineering' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/registry/systems' -Method Post -ContentType 'application/json' -Body $body
```

Registering the same name and version twice returns HTTP 409.

### Tests

```bash
docker compose exec backend pytest -q     # 118 tests
```

Tests mock the LLM, so they cost nothing and are deterministic.

---

## Demos

The demo models use **synthetic data**. Both demos inject their problem on purpose so the monitor has something to find. These are simulations, not natural findings.

Thresholds (`.env`): demographic parity and equalized odds warning 0.05, critical 0.10. PSI info 0.10, warning 0.20, critical 0.25.

### Demo 1: bias detection

Training with `--inject-bias` flips 35% of under-30 "good" labels to "default" before training, which simulates historically biased lending data.

```powershell
python demo_models/credit_scoring/train.py --inject-bias --output demo_models/credit_scoring/artifacts
python scripts/run_bias_demo.py --system-id <system_id>
```

Measured: approval rate under 30 was 10.96%, for 30+ it was 35.76%. Demographic parity difference 0.248, equalized odds difference 0.329. Two CRITICAL alerts fired, referencing EU AI Act Article 10(2) (data governance, including bias examination). That reference is a mapping to a relevant provision, not a legal finding. RBI references are displayed as "RBI: not assessed (no corpus indexed)".

### Demo 2: input drift

Training with `--drift` adds an additive stress shift to features V1, V3 and V14, simulating an economic stress event.

```powershell
python demo_models/fraud_detection/train.py --drift --drift-strength 1.5 --output demo_models/fraud_detection/artifacts
python scripts/run_drift_demo.py --system-id <system_id>
```

Measured: V1 PSI 0.894, V3 PSI 1.020, V14 PSI 0.829; overall PSI 0.132 (diluted across 20 features). Alerts are raised per feature, so three CRITICAL alerts fired. PSI bins come from the reference data only, and out-of-range current values fall into the edge buckets.

### Demo 3: regulatory change propagation

Run once with a clearly synthetic update that required extended record-keeping for creditworthiness systems. It flagged the credit scoring system only (correct), and created tasks with valid system references, plus one extra task the update did not ask for. Review generated tasks before acting on them. Details in `docs/qa_propagation_eval.md`. There is no dashboard UI for this.

---

## Evaluation

Risk-tier classification was evaluated on three sets of hand-labelled cases using `gemini-3.5-flash-lite`. The sets are reported separately because they differ in difficulty and were made under different conditions. Samples are small, so none of these is an accuracy estimate.

| Set | Cases | Tier accuracy | Notes |
|---|---|---|---|
| Labelled set | 15 | 15/15 | Written alongside the system, so the easiest set |
| Held-out | 10 | 9/10 | Labels committed before the run; found a false negative (below) |
| Fresh | 7 | 6/7 | Written and committed after the fix; included a control |

**The failure that mattered.** In the held-out run, a system that exploits elderly customers' age-related vulnerabilities (a prohibited practice under Article 5(1)(b)) was classified MINIMAL_RISK. The cause was retrieval: Article 5 is split across several chunks, only one was pinned, and the pinned chunk changed between runs because LLM-inferred fields altered the query. The fix pins all of Article 5(1) and makes retrieval depend only on the user's description. On the fresh set, 3 of 4 prohibited cases were then caught.

**The remaining miss** was a "future crime profiler" classified HIGH_RISK under Annex III point 6(d) instead of PROHIBITED under Article 5(1)(d). The two provisions overlap, so this is a genuine boundary case, but the model also had Article 5(1)(d) in context and chose the high-risk reading.

**Citation matching.** Exact-string matching of citations scored low (2/15 on the first set) because the model returns split fields such as `article: "Article 5", point: "f"`. After canonicalisation, supporting-citation matches were 11/15 (first set, by a rule written after seeing results), 6/10 (held-out) and 6/7 (fresh). Full tables and quoted reasoning are in `docs/`.

**Retrieval.** A 6-query retrieval check passes 6/6, with credit scoring returning Annex III point 5(b) at rank 1. Treat that as a regression test, not a quality estimate: the queries were written alongside the fix, and Article 6 is now pinned into every context.

**Q&A.** On 10 questions, 8 were correct and 2 partly correct. The partial answers (Article 14 and Article 50) omitted qualifications from the retrieved text. Registry questions are answered by SQL with zero LLM calls, so those answers are correct by construction and test routing only.

---

## Audit dossier

`POST /api/v1/audit/generate-dossier` (or the Audit page) produces a PDF containing the system overview, the classification with provider, model, confidence, review flags and reasoning, an advisory notice, fairness and drift history, alerts with metric and compared groups, remediation tasks, and audit metadata. The credit scoring dossier is 5 pages.

- The PDF's SHA-256 is stored in the audit record. The "source HTML hash" printed inside the PDF is a different value, because a file cannot contain its own hash.
- The hash makes tampering with a downloaded copy **detectable**. It does not make it impossible: it lives in the same database, so someone who can write to the database could change both.
- The dossier lists the eight EU AI Act obligations that apply to high-risk systems (Articles 9 to 15 and 43) as requirements. It does **not** mark them compliant or non-compliant, because the absence of an alert does not prove compliance.
- Generation time was about 3 seconds for an earlier 10-page version; the current version has not been re-timed.

---

## Dashboard

React pages: Dashboard (counts and recent systems), Registry, Monitoring (alerts with metric, feature, value against threshold, and a Resolve button), Audit (choose a system, generate, download), and System Detail (classification cards, citations, snapshots, alerts, model card). Governance Q&A is available through the API (`POST /api/v1/qa/ask`) and has no dashboard page.

---

## Known limitations

- **Small LLM, small samples.** Classification used a small free-tier model on 32 hand-written cases, and I wrote both the descriptions and the labels. Boundary cases (prohibited versus high-risk in law enforcement and biometrics) are the weak spot.
- **`needs_review` is not an error detector.** It flags internal problems (low confidence, schema repair, dropped citations). A confident, well-formed, wrong answer will not trigger it, and a missed prohibition is exactly such a case.
- **Confidence values are not probabilities.** The same description received 0.98 on one run and 0.95 on another.
- **RBI is not assessed.** No RBI corpus is indexed. DPDP Act and EBA guidelines are planned and not implemented.
- **Authentication is a development stub.** Requests without credentials are treated as admin. Do not expose this to a network. OAuth2 and role-based access control are planned.
- **Not fully "no external dependencies".** Classification and Q&A send system descriptions and retrieved public regulatory text to a hosted LLM. A local-model provider is not implemented. This is by design and has not been independently audited.
- **Regulation answers can omit qualifications.** Read the cited provision before relying on a summary.
- **The audit PDF is a record, not a compliance verdict.**
- **The demo data is synthetic and the problems are injected.**
- **Regulatory timelines move.** The EU AI Act entered into force in 2024 with obligations phasing in, and the dates for some obligations have been subject to proposed changes. Check current dates before relying on any statement about what applies when.

---

## Roadmap

`[x]` done and used, `[~]` implemented but only partly validated, `[ ]` planned.

- [x] AI system registry with duplicate protection
- [x] Structure-aware RAG over the EU AI Act, with provenance metadata
- [x] LLM classification with grounding checks, canonical citations, and review flags
- [x] Fairness and drift monitoring with per-feature PSI alerts
- [x] Audit dossier PDF with stored SHA-256
- [x] React dashboard (registry, monitoring, audit, system detail)
- [~] Regulatory propagation agent (one synthetic run)
- [~] Governance Q&A (10-question check, API only)
- [~] Anthropic provider (implemented, not run live)
- [~] Prometheus metrics endpoint (no Grafana dashboard)
- [ ] RBI corpus and assessment
- [ ] DPDP Act and EBA frameworks
- [ ] OAuth2 and role-based access control
- [ ] Local-model provider
- [ ] Q&A page in the dashboard
- [ ] Larger, independently labelled evaluation set

---

## Project layout (abridged)

```
argus/
  argus/
    api/routers/        registry, monitoring, audit, Q&A
    core/               agents, llm layer, citations, schemas, registry service
    rag/                ingestion, retriever, prohibition screen
    db/
  dashboard/            React frontend
  demo_models/          credit_scoring, fraud_detection, doc_classifier
  scripts/              demo runners, evaluation runners
  tests/                118 tests, plus evaluation fixtures
  docs/                 evaluation reports
  regulations/pdfs/     put eu_ai_act.pdf here
  docker-compose.yml
```

---

## Why this exists

Banks deploy AI in credit, fraud, and hiring, which are the areas the EU AI Act treats as high-risk or restricts. Teams that manage this in spreadsheets struggle to say which systems exist, what tier each falls into, and whether anyone is watching them. ARGUS explores what a governed inventory with grounded classification, monitoring and audit output could look like.

## License

MIT License. See [LICENSE](LICENSE).