# ARGUS — AI Governance & Risk Unified System

> An enterprise-grade, multi-agent platform for governing AI systems at scale — built for regulated industries like banking and financial services.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-red.svg)]()

---

## The Problem

Large financial institutions deploy hundreds of AI systems simultaneously — credit scoring models, fraud detectors, document classifiers, trading algorithms. Each one needs to be:

- **Inventoried** — catalogued with ownership, data sources, and purpose
- **Risk-classified** — under frameworks like the EU AI Act, some systems carry mandatory legal obligations
- **Monitored** — for fairness violations, output drift, and behavioral changes
- **Audit-ready** — regulators can demand compliance evidence at any time

Today, most banks manage this through Excel spreadsheets and manual Confluence pages. ARGUS replaces that with an autonomous, intelligent governance layer.

---

## What ARGUS Does

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARGUS PLATFORM                           │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  AI System  │  │     Risk     │  │  Fairness & Drift   │    │
│  │  Registry   │─▶│  Classifier  │  │      Monitor        │    │
│  │   Agent     │  │    Agent     │  │       Agent         │    │
│  └─────────────┘  └──────────────┘  └────────────────────┘    │
│         │                │                     │               │
│         ▼                ▼                     ▼               │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              PostgreSQL + pgvector                   │       │
│  │     (AI System Registry + Regulatory RAG Store)      │       │
│  └─────────────────────────────────────────────────────┘       │
│         │                │                     │               │
│         ▼                ▼                     ▼               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Regulatory │  │    Audit     │  │    Governance       │    │
│  │  Propagation│  │   Evidence   │  │      Q&A            │    │
│  │    Agent    │  │   Generator  │  │    Interface        │    │
│  └─────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Five Core Agents

| Agent | Responsibility |
|---|---|
| **Registrar** | Ingests new AI system submissions, extracts metadata, generates model cards |
| **Risk Classifier** | Classifies systems by EU AI Act / RBI risk tier; RAG/Claude-backed citations are not yet validated |
| **Drift & Fairness Monitor** | Tracks demographic parity, equalized odds, PSI drift — raises tiered alerts |
| **Regulatory Propagation** | Monitors regulatory update feeds, maps changes to affected systems, assigns remediation tasks |
| **Audit Evidence Generator** | Produces PDF audit dossiers on demand; generation timing is not yet measured |

---

## Regulatory Frameworks Supported

| Framework | Jurisdiction | Status |
|---|---|---|
| EU AI Act (2024/1689) | European Union | Code exists; fallback verified |
| RBI Guidelines on Model Risk Management | India | Code exists; fallback verified |
| DPDP Act 2023 | India | Planned |
| EBA Guidelines on Internal Governance | EU Banking | Planned |

---

## Tech Stack

```
Backend:         Python 3.11, FastAPI
Agent Framework: Standalone Python agents (LangGraph orchestration planned)
LLM:             Anthropic Claude API (optional; real Claude path not validated)
RAG Pipeline:    pgvector + LangChain (PDF corpus/index not included)
Database:        PostgreSQL 16
Fairness:        fairlearn, scipy (PSI, demographic parity, equalized odds)
PDF Generation:  WeasyPrint + Jinja2
Frontend:        React 18 + TypeScript + shadcn/ui
Auth:            Development JWT stub; OAuth2/RBAC planned
Infra:           Docker + Docker Compose (fully self-hostable)
Monitoring:      Prometheus metrics endpoint
```

> **Design principle:** Fully self-hostable with no external SaaS dependencies. Sensitive model metadata never leaves the enterprise network.

---

## Project Structure

```
argus/
├── argus/
│   ├── core/
│   │   ├── agents/             # Five Python agents
│   │   │   ├── registrar.py
│   │   │   ├── risk_classifier.py
│   │   │   ├── drift_monitor.py
│   │   │   ├── reg_propagation.py
│   │   │   └── audit_generator.py
│   │   ├── registry/           # AI System Registry (models + service)
│   │   ├── rag/                # RAG pipeline over regulatory PDFs
│   │   └── fairness/           # Fairness metrics + drift detection
│   ├── api/
│   │   ├── main.py             # FastAPI app entrypoint
│   │   └── routers/            # Registry, monitoring, audit endpoints
│   └── db/                     # Database connection + migrations
├── dashboard/                  # React frontend
├── demo_models/                # Sample AI models for demonstration
│   ├── credit_scoring/         # XGBoost credit risk model (synthetic data)
│   ├── fraud_detection/        # Fraud detection model with drift injection
│   └── doc_classifier/         # Document type classifier
├── regulations/                # Regulatory document ingestion pipeline
├── policies/                   # YAML-based governance policy configs
├── docs/                       # Architecture + API documentation
└── docker-compose.yml
```

---

## Quickstart

### Prerequisites
- Docker & Docker Compose
- Anthropic API key

### Run with Docker
```bash
git clone https://github.com/YOUR_USERNAME/argus.git
cd argus
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
docker-compose up --build
```

Visit `http://localhost:3000` for the dashboard, `http://localhost:8000/docs` for the API.

Frontend preview:

```bash
cd dashboard
npm start
```

### Ingest Regulatory Documents
```bash
# Download EU AI Act PDF and place in regulations/pdfs/
python -m argus.rag.ingestion --source regulations/pdfs/eu_ai_act.pdf --framework EU_AI_ACT

# Download RBI Model Risk Guidelines
python -m argus.rag.ingestion --source regulations/pdfs/rbi_model_risk.pdf --framework RBI
```

### Register Your First AI System
```bash
curl -X POST http://localhost:8000/api/v1/registry/systems \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Credit Scoring Model v2",
    "purpose": "Predicts probability of loan default using applicant transaction history",
    "data_sources": ["transaction_history", "credit_bureau"],
    "output_type": "binary_classification",
    "affected_demographics": ["age", "income_band"],
    "jurisdictions": ["EU", "IN"],
    "owner_team": "retail-credit-engineering"
  }'
```

ARGUS will classify its risk tier and begin monitoring. Article-level citations require indexed regulatory documents and a validated Claude/RAG path.

---

## Demo

Three pre-built demo models are included to showcase ARGUS capabilities out of the box.

### Demo Scenario 1 — Bias Detection
The included credit scoring model uses synthetic data. Bias is injected deliberately with `--inject-bias`: a fraction of under-30 good labels are flipped to default labels before training. Run from the nested `argus` project directory in PowerShell:

```powershell
python demo_models/credit_scoring/train.py --inject-bias --output demo_models/credit_scoring/artifacts
$env:ANTHROPIC_API_KEY=''
uvicorn argus.api.main:app --host 127.0.0.1 --port 8000
$body = @{ name = 'Credit Scoring Engine v2'; purpose = 'Evaluate creditworthiness of loan applicants using credit history, income, and debt ratios'; owner_team = 'Risk Analytics'; data_sources = @('credit_bureau','income_verification','transaction_data'); affected_demographics = @('age','gender','income_level'); jurisdictions = @('EU','IN') } | ConvertTo-Json
$system = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/registry/systems' -Method Post -ContentType 'application/json' -Body $body
python scripts/run_bias_demo.py --system-id $system.system_id
```

Measured output: approval rate under 30 was 10.96%, approval rate for 30+ was 35.76%, and the demographic parity gap was 24.8%. ARGUS created a CRITICAL alert referencing `EU AI Act Article 10(2); RBI Model Risk Section 4.3`.

### Demo Scenario 2 — Input Drift
The fraud model uses an additive stress shift on V1, V3, and V14. Run from the nested `argus` project directory in PowerShell:

```powershell
python demo_models/fraud_detection/train.py --drift --drift-strength 1.5 --output demo_models/fraud_detection/artifacts
$body = @{ name = 'Fraud Detection Engine'; purpose = 'Classify financial transactions as fraudulent or legitimate using behavioral patterns and transaction features'; owner_team = 'Financial Crime AI'; data_sources = @('transaction_stream','device_data','merchant_data'); affected_demographics = @('geography'); jurisdictions = @('EU','IN') } | ConvertTo-Json
$system = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/registry/systems' -Method Post -ContentType 'application/json' -Body $body
python scripts/run_drift_demo.py --system-id $system.system_id
```

Measured output with the default strength `1.5`: V1 PSI was 0.893621, V3 PSI was 1.019934, V14 PSI was 0.828686, and overall PSI was 0.132430. Three CRITICAL input-drift alerts fired, each referencing `RBI Model Risk Guidelines Section 5.1`.

### Demo Scenario 3 — Regulatory Change Propagation
The propagation agent code exists, but this workflow has not been validated end to end. Treat dropping an update file into `regulations/updates/` as planned demo work.

---

`[~]` means implemented in code but not fully validated against real Claude, regulatory PDFs, or production services.

## Roadmap

- [x] AI System Registry with structured metadata schema
- [~] RAG pipeline over EU AI Act + RBI guidelines (code exists; corpus/search not validated)
- [~] Risk classification agent with article-level citations (fallback verified; Claude/RAG not validated)
- [~] Fairness monitoring metrics and alerts (backend validated; dashboard is limited)
- [~] Regulatory change propagation agent (code exists; end-to-end path not validated)
- [~] Audit evidence PDF generator (test validated; timing not measured)
- [ ] DPDP Act 2023 integration (planned)
- [~] Governance Q&A endpoint (fallback path exists; Claude path/dashboard not validated)
- [~] Prometheus metrics endpoint (Grafana dashboard planned)
- [ ] OAuth2 and role-based access control (development auth stub currently accepts anonymous requests)
- [ ] LangGraph orchestration (planned)

---

## Why ARGUS Exists

The EU AI Act came into full effect in 2025. For banks, this means every AI system touching credit, fraud, or employment decisions carries mandatory legal obligations — conformity assessments, explainability requirements, human oversight documentation, and audit trails.

ARGUS is the internal tooling layer that makes compliance operationally tractable, replacing manual processes with autonomous agents that monitor, classify, and document continuously.

---

## Contributing

This project is under active development. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
