# ARGUS — AI Governance & Risk Unified System

**Enterprise platform for governing every AI system banks deploy**, across EU AI Act and RBI regulatory frameworks.

## Overview

ARGUS is a production-ready AI governance platform that automates the governance, classification, monitoring, and compliance management of AI systems in regulated industries. It implements five autonomous agents that work together to ensure regulatory compliance, detect fairness violations, and maintain audit trails.

### The Five Autonomous Agents

| Agent | Responsibility |
|-------|-----------------|
| **Registrar** | Intake new AI systems, extract metadata, generate model cards via Claude |
| **Risk Classifier** | Classify systems under EU AI Act + RBI guidelines using RAG over regulatory PDFs |
| **Drift & Fairness Monitor** | Detect demographic bias + data drift using fairlearn + PSI |
| **Regulatory Propagation** | Watch for regulation updates, identify affected systems, auto-create remediation tasks |
| **Audit Generator** | Produce regulator-ready PDF dossiers on demand in <30 seconds |

### Supported Regulatory Frameworks

| Framework | Coverage | Status |
|-----------|----------|--------|
| **EU AI Act** (Regulation 2024/1689) | Article 5 (Prohibited), Annex III (High-Risk), Articles 10-15 (Fairness) | ✓ Implemented |
| **RBI Model Risk Guidelines** | Model classification, validation, monitoring, governance | ✓ Implemented |
| **Indian DPDP Act** | Personal data protection requirements | ✓ Supported |
| **EBA Guidelines** | Banking AI governance (extensible) | ✓ Supported |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ARGUS Platform                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Registrar   │  │ Risk         │  │ Drift &      │       │
│  │  Agent       │  │ Classifier   │  │ Fairness     │       │
│  │              │  │  Agent       │  │ Monitor      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Regulatory   │  │ Audit        │                         │
│  │ Propagation  │  │ Generator    │                         │
│  │  Agent       │  │  Agent       │                         │
│  └──────────────┘  └──────────────┘                         │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ FastAPI      │  │   RAG        │  │  Registry    │       │
│  │ Application  │  │  Pipeline    │  │  Service     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         PostgreSQL + pgvector                        │  │
│  │  (AI Systems, Alerts, Snapshots, Regulatory Docs)  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Stack

- **Language**: Python 3.11 + TypeScript/React
- **API**: FastAPI with async/await
- **Database**: PostgreSQL with pgvector for embeddings
- **LLM**: Anthropic Claude API
- **RAG**: LangChain + LangGraph + pgvector
- **Fairness**: fairlearn + scikit-learn
- **ML Models**: XGBoost, Random Forest
- **PDF Generation**: WeasyPrint
- **Frontend**: React 18 with TypeScript
- **Monitoring**: Prometheus + Grafana (optional)
- **Deployment**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16+ (if not using Docker)
- Anthropic API key

### Installation

1. **Clone and setup**

```bash
cd argus
cp .env.example .env
# Edit .env with your API key and database settings
```

2. **Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Initialize database**

```bash
python -c "import asyncio; from argus.db.database import create_db_and_tables; asyncio.run(create_db_and_tables())"
```

4. **Start the API**

```bash
uvicorn argus.api.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# Services available:
# - API: http://localhost:8000
# - Dashboard: http://localhost:3000
# - Prometheus: http://localhost:9090
# - PostgreSQL: localhost:5432

# View logs
docker-compose logs -f backend

# Shutdown
docker-compose down -v
```

## Ingest Regulatory Documents

ARGUS uses RAG to provide up-to-date regulatory guidance. Load regulatory PDFs:

```bash
# EU AI Act
python -m argus.rag.ingestion \
  --source "path/to/EU-AI-Act.pdf" \
  --framework EU_AI_ACT

# RBI Guidelines
python -m argus.rag.ingestion \
  --source "path/to/RBI-Model-Risk-Guidelines.pdf" \
  --framework RBI

# Indian DPDP Act
python -m argus.rag.ingestion \
  --source "path/to/DPDP-Act.pdf" \
  --framework DPDP
```

Where to find regulatory documents:
- **EU AI Act**: https://eur-lex.europa.eu/ (Search: "Regulation 2024/1689")
- **RBI Guidelines**: https://www.rbi.org.in/CommonMan/English/Scripts/Notification.aspx (Search: "Model Risk Management")
- **Indian DPDP Act**: https://www.meity.gov.in/

## Demo Scenario

### 1. Register a Credit Scoring System

```bash
curl -X POST http://localhost:8000/api/v1/registry/systems \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Credit Scoring Engine v2",
    "purpose": "Evaluate creditworthiness of loan applicants using credit history, income, and debt ratios",
    "owner_team": "Risk Analytics",
    "owner_email": "risk@bank.com",
    "data_sources": ["credit_bureau", "income_verification", "transaction_data"],
    "affected_demographics": ["age", "gender", "income_level"],
    "jurisdictions": ["EU", "IN"]
  }'
```

Expected response:
- System registered with ID like `credit-scoring-engine-v2-a1b2c3`
- Risk tier: `HIGH_RISK` (loan decision system)
- Model card generated automatically
- EU AI Act obligations extracted

### 2. Evaluate for Fairness

```bash
curl -X POST http://localhost:8000/api/v1/monitoring/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "system_id": "credit-scoring-engine-v2-a1b2c3",
    "y_true": [1, 0, 1, 1, 0, ...],
    "y_pred": [1, 0, 1, 0, 0, ...],
    "y_proba": [0.92, 0.15, 0.88, 0.45, 0.22, ...],
    "sensitive_feature_name": "age_group",
    "sensitive_feature_values": ["30_45", "under_30", "over_60", ...],
    "reference_data": [{...}, {...}],
    "current_data": [{...}, {...}]
  }'
```

Expected response:
- Fairness metrics: Demographic Parity, Equalized Odds
- Drift detection: PSI per feature
- Alerts created for violations
- Example: "Demographic parity diff = 0.12 (CRITICAL)" → Auto-alert created

### 3. Generate Audit Dossier

```bash
curl -X POST http://localhost:8000/api/v1/audit/generate-dossier \
  -H "Content-Type: application/json" \
  -d '{
    "system_id": "credit-scoring-engine-v2-a1b2c3",
    "requested_by": "compliance_officer@bank.com"
  }'
```

Expected response:
- PDF generated in < 30 seconds
- Includes system overview, risk classification, fairness history, alerts, compliance checklist
- SHA-256 hash for integrity verification
- Ready for regulator submission

## API Endpoints

### Registry

```
POST   /api/v1/registry/systems              — Register system
GET    /api/v1/registry/systems              — List systems
GET    /api/v1/registry/systems/{id}         — Get system details
DELETE /api/v1/registry/systems/{id}         — Soft delete
POST   /api/v1/registry/systems/{id}/reclassify  — Re-classify risk
GET    /api/v1/registry/systems/{id}/model-card  — Get model card
```

### Monitoring

```
POST   /api/v1/monitoring/evaluate           — Run fairness evaluation
GET    /api/v1/monitoring/systems/{id}/snapshots  — Fairness history
GET    /api/v1/monitoring/alerts             — List alerts
POST   /api/v1/monitoring/alerts/{id}/resolve     — Resolve alert
GET    /api/v1/monitoring/systems/{id}/compliance — Compliance status
```

### Audit

```
POST   /api/v1/audit/generate-dossier       — Generate PDF
GET    /api/v1/audit/records                — List records
GET    /api/v1/audit/records/{id}/download  — Download PDF
```

### Q&A

```
POST   /api/v1/qa/ask                       — Governance Q&A
```

## Testing

```bash
# Run unit tests
pytest tests/ -v

# Coverage report
pytest tests/ --cov=argus --cov-report=html

# Run linter
ruff check argus/
```

## Key Design Decisions

### 1. Why Claude vs. Open Source LLMs?

- **Accuracy**: EU AI Act classification requires precise regulatory understanding
- **Reasoning**: Claude's chain-of-thought excels at regulatory interpretation
- **Context window**: Can process entire regulatory documents in single request
- **Reliability**: Enterprise-grade for production compliance use

### 2. Why pgvector?

- **Semantic search**: Retrieves relevant regulatory passages during classification
- **Single database**: Eliminates separate vector DB complexity
- **ACID transactions**: Ensures consistency in regulated environment
- **Proven in production**: Used by financial institutions globally

### 3. Why LangGraph?

- **Agent orchestration**: Coordinates multi-step regulatory workflows
- **State management**: Maintains context across system classification steps
- **Extensibility**: New agents can be added without refactoring core

## Deployment

### Production Checklist

- [ ] Use external PostgreSQL (not Docker)
- [ ] Enable SSL/TLS for API
- [ ] Rotate JWT_SECRET
- [ ] Configure Anthropic API key securely (use AWS Secrets Manager, etc.)
- [ ] Set up log aggregation (ELK Stack or DataDog)
- [ ] Enable Prometheus monitoring
- [ ] Configure Slack/PagerDuty for critical alerts
- [ ] Test audit PDF generation with regulators
- [ ] Set up automated regulatory document ingestion

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connectivity
curl -X GET http://localhost:8000/api/v1/registry/systems

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Troubleshooting

### Database connection refused

```bash
# Check PostgreSQL is running
psql -U argus -h localhost -d argus -c "SELECT 1"

# Docker: restart db service
docker-compose restart db
```

### Anthropic API errors

```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# Verify key has quota
# https://console.anthropic.com/account/usage
```

### Out of memory during PDF generation

```bash
# Increase Docker memory limit
# docker-compose.yml: services.backend.mem_limit: 2g
```

## Contributing

Development workflow:

```bash
# Create feature branch
git checkout -b feature/new-agent

# Make changes, test
pytest tests/

# Lint
ruff check argus/

# Commit and push
git push origin feature/new-agent
```

## Roadmap

- [ ] Support for NIST AI RMF framework
- [ ] GraphQL API alongside REST
- [ ] Multi-tenant governance (separate orgs)
- [ ] Automated bias remediation recommendations
- [ ] Model explainability dashboard (SHAP values)
- [ ] Integration with model registries (HuggingFace, MLflow)
- [ ] Mobile app for on-the-go compliance reviews
- [ ] Blockchain audit trail immutability

## Support & Contact

For questions or issues:

1. Check [FAQ](docs/FAQ.md)
2. Search existing [GitHub Issues](https://github.com/argus-ai-gov/argus/issues)
3. Create a new issue with full context

## License

Proprietary — Restricted to authorized financial institutions

## Disclaimer

This system provides governance recommendations but **does not replace human compliance judgment**. Regulators have final authority on AI system classification and remediation requirements. ARGUS augments human decision-making, not replaces it.

---

**ARGUS Version 1.0.0** | Last Updated: May 2026
