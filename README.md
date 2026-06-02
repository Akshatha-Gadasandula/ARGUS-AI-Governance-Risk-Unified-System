# ARGUS — AI Governance & Risk Unified System

> An enterprise-grade, multi-agent platform for governing AI systems at scale — built for regulated industries like banking and financial services.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
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
| **Risk Classifier** | Classifies systems by EU AI Act / RBI / DPDP Act risk tier with article-level citations via RAG |
| **Drift & Fairness Monitor** | Tracks demographic parity, equalized odds, PSI drift — raises tiered alerts |
| **Regulatory Propagation** | Monitors regulatory update feeds, maps changes to affected systems, assigns remediation tasks |
| **Audit Evidence Generator** | Produces regulator-ready PDF dossiers on demand in under 30 seconds |

---

## Regulatory Frameworks Supported

| Framework | Jurisdiction | Status |
|---|---|---|
| EU AI Act (2024/1689) | European Union | ✅ Implemented |
| RBI Guidelines on Model Risk Management | India | ✅ Implemented |
| DPDP Act 2023 | India | 🔄 In Progress |
| EBA Guidelines on Internal Governance | EU Banking | 🔄 In Progress |

---

## Tech Stack

```
Backend:         Python 3.11, FastAPI
Agent Framework: LangGraph (multi-agent orchestration)
LLM:             Anthropic Claude API (claude-sonnet-4-6)
RAG Pipeline:    pgvector + LangChain (EU AI Act, RBI Guidelines indexed)
Database:        PostgreSQL 16
Fairness:        fairlearn, scipy (PSI, demographic parity, equalized odds)
PDF Generation:  WeasyPrint + Jinja2
Frontend:        React 18 + TypeScript + shadcn/ui
Auth:            OAuth2 + JWT, Role-based access control
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
│   │   ├── agents/             # Five LangGraph agents
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
│   ├── credit_scoring/         # XGBoost credit risk model (public dataset)
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

ARGUS will automatically classify its risk tier, cite relevant regulatory articles, and begin monitoring.

---

## Demo

Three pre-built demo models are included to showcase ARGUS capabilities out of the box.

### Demo Scenario 1 — Bias Detection
The included credit scoring model (`demo_models/credit_scoring/`) is trained with a deliberate demographic imbalance. ARGUS's fairness monitor detects and raises:

```
CRITICAL ALERT — Model: credit-scoring-v2 (High-Risk, EU AI Act Article 6)
Demographic parity violation detected.
Approval rate age < 30: 61.2% | age ≥ 30: 74.8%
Disparity: 13.6% — exceeds 10% policy threshold
Regulatory reference: EU AI Act Article 10(2), Annex III Point 5(b)
Action required within: 72 hours
```

### Demo Scenario 2 — Input Drift
The fraud detection model (`demo_models/fraud_detection/`) includes a drift injection script. Run it to watch ARGUS raise a PSI-based drift alert with automatic feature attribution.

### Demo Scenario 3 — Regulatory Change Propagation
Drop any `.txt` file into `regulations/updates/` describing a policy change. The propagation agent identifies affected systems and generates remediation tasks automatically.

---

## Roadmap

- [x] AI System Registry with structured metadata schema
- [x] RAG pipeline over EU AI Act + RBI guidelines
- [x] Risk classification agent with article-level citations
- [ ] Fairness monitoring dashboard (PSI, demographic parity, equalized odds)
- [ ] Regulatory change propagation agent
- [ ] Audit evidence PDF generator
- [ ] DPDP Act 2023 integration
- [ ] Governance Q&A interface
- [ ] Prometheus metrics + Grafana dashboard
- [ ] Role-based access control (Owner / Compliance Officer / Admin)

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
