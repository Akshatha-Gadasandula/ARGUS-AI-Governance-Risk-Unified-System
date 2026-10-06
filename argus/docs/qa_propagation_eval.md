# Q&A and regulatory propagation evaluation

Measured 2026-10-06. Measurement only: application prompts, thresholds, retrieval, labels and source code were unchanged. Provider: gemini; model: gemini-3.5-flash-lite.

## Inspection before live calls

Both entry points use `argus/core/llm.py` via `get_llm(settings).generate_json`. Neither bypasses the shared provider/cache/cap/throttle/schema-validation/grounding layer. Source SHA-256 values matched between the workspace and container before the run.

**Propagation entry point:** `RegPropagationAgent.process_file(file_path, session)` in `argus/core/agents/reg_propagation.py`; a separate `watch(...)` loop can scan `.txt` files, but no watcher was started. `process_file` reads the file, calls UpdateOutput generation, reads active AISystem records (name, public system_id, first 100 purpose characters, owner_team/UUID for tasks), and calls AffectedSystemsOutput generation. Two normal live calls. It writes one RegulatoryUpdate, a RemediationTask and GovernanceAlert per required action and affected system, committing through RegistryService, then renames the input to `.processed`. It returns an integer task count, not an HTTP response. UpdateOutput fields: framework, title, summary, affected_articles, urgency, required_actions. Impact fields: system_ids. The shared layer adds llm_provider, llm_model, needs_review, needs_review_reasons and dropped_citations. Raw impact IDs can be invented and silently discarded by the object-selection step, so this evaluation checked the raw list as well as stored rows. Due dates are application policy: HIGH 30, MEDIUM 90, LOW 180 days.

**Q&A entry point:** POST `/api/v1/qa/ask` -> `answer_question` in `argus/api/routers/qa.py`. Request: question string, minimum five characters. Each uncached request normally uses TWO live calls: QueryTypeOutput classification, then AnswerOutput generation. Registry queries read active systems and send names, IDs, the first 100 purpose characters and tiers; they do not send stored classification reasoning. Alert queries read the ten newest CRITICAL/WARNING alerts, without filtering resolved status, joining system names, or including system IDs; they send only date, severity and title. Compliance queries retrieve five EU_AI_ACT chunks and the shared layer appends their text and metadata to the prompt. General queries receive no database or corpus context and have no deterministic out-of-scope guard. Q&A writes no database records; its shared layer writes cache/usage files. Response fields: answer, sources, citations, query_type, llm_provider, llm_model, needs_review. It does not expose needs_review_reasons in QAResponse. Sources for registry/alerts/general are handler-assigned labels, rather than model-generated per-claim provenance. Provider/invalid-JSON fallbacks may produce generic mock answers.

**UPDATE_DIR:** local `argus/.env` contains `policies/updates`. Docker environment and container dotenv have no UPDATE_DIR, and Settings has no update_dir field. This one-shot measurement explicitly used the local configured path at `/app/policies/updates`, which is a bind mount. The application does not wire the watcher into startup.

## Budget and transport

Hard total allowance: 12 live Gemini calls. Propagation allowance: 5; Q&A allowance: 6. All six classification prompts were cache misses before the run. Therefore six Q&A questions would normally require 12 Q&A calls, exceeding both its six-call allowance and the overall allowance when combined with propagation. A preference question was sent; with no reply before execution, questions 1-3 were selected in order. Questions 4-6 were NOT executed and are not graded as model failures. No question was rerun.

Propagation estimated 2 calls, with a process-local cap of 5. Q&A estimated 6 calls for questions 1-3, with a process-local cap of 6. These caps did not edit the application source or persistent env settings. Q&A used real HTTP POSTs to the unchanged FastAPI application at `http://127.0.0.1:8001/api/v1/qa/ask` inside the backend container, through an isolated temporary listener. It was shut down and awaited in finally. The existing port-8000 server was not restarted; these were not requests to its resident process. Initial inspection/ground truth did use the running port-8000 API.

## Ground truth, computed before Q&A

- Q1: only `credit_scoring_model-4dbb0f` is HIGH_RISK.
- Q2: `credit_scoring_model-4dbb0f` and `fraud_detection_engi-2a6271` have unresolved CRITICAL alerts.
- Q3: `email_spam_filter-c64b88` is MINIMAL_RISK. Its stored EU_AI_ACT reasoning excludes prohibited practices, Annex III high-risk categories, and Article 50 transparency categories; ordinary spam classification falls into the default minimal category.
- Q4: credit scoring has 3 open alerts, all CRITICAL. Fraud has 3 open CRITICAL alerts; spam has none.

## Regulatory propagation: completed once

Synthetic file, no system names:

```text
SYNTHETIC TEST UPDATE - not a real regulation
This synthetic test requires extended record-keeping and human review for AI systems that evaluate the creditworthiness of natural persons. It applies only to those systems. This is a test scenario and must not be treated as an actual regulatory requirement.
```

Expected and returned affected IDs: `credit_scoring_model-4dbb0f` only. Fraud and spam were not affected. Every raw returned ID exists in the database; all three stored tasks had valid system and regulatory-update foreign keys. No invented system or statutory provision was returned; affected_articles was empty. Both generation outputs had needs_review=false. The model inferred EU_AI_ACT and LOW urgency although neither was specified by the synthetic text. The third task, 'Verify test scenario parameters', is an additional model-generated action, not an explicit requirement in the synthetic update. The 180-day due-date policy is not a deadline supplied by the test text.

### Stored tasks (checked before cleanup)

- `03be70f7-2489-4e69-9280-84a87140a8fd` -> `credit_scoring_model-4dbb0f`; system FK valid=True, update FK valid=True.

  Title: [EU_AI_ACT] Review system capabilities for extended record-keeping

```text
Required action from regulatory update: Synthetic Test Update for Creditworthiness AI Systems

Summary: This synthetic test scenario introduces requirements for extended record-keeping and mandatory human review specifically for AI systems that evaluate the creditworthiness of natural persons. It is a test update and does not constitute a real regulatory requirement.

LLM provider: gemini; LLM model: gemini-3.5-flash-lite
Affected articles: 
```

- `e9630d75-d783-4de0-969d-ce10e193a731` -> `credit_scoring_model-4dbb0f`; system FK valid=True, update FK valid=True.

  Title: [EU_AI_ACT] Implement human review mechanisms for creditworthiness evaluations

```text
Required action from regulatory update: Synthetic Test Update for Creditworthiness AI Systems

Summary: This synthetic test scenario introduces requirements for extended record-keeping and mandatory human review specifically for AI systems that evaluate the creditworthiness of natural persons. It is a test update and does not constitute a real regulatory requirement.

LLM provider: gemini; LLM model: gemini-3.5-flash-lite
Affected articles: 
```

- `6381b1f7-6b73-4e86-b2dd-581176be357d` -> `credit_scoring_model-4dbb0f`; system FK valid=True, update FK valid=True.

  Title: [EU_AI_ACT] Verify test scenario parameters

```text
Required action from regulatory update: Synthetic Test Update for Creditworthiness AI Systems

Summary: This synthetic test scenario introduces requirements for extended record-keeping and mandatory human review specifically for AI systems that evaluate the creditworthiness of natural persons. It is a test update and does not constitute a real regulatory requirement.

LLM provider: gemini; LLM model: gemini-3.5-flash-lite
Affected articles: 
```

### Cleanup

Only rows created by this run were deleted, including synthetic alerts/update to avoid leaving test governance issues behind. Database re-queries confirmed their absence.

remediation_tasks:
- `03be70f7-2489-4e69-9280-84a87140a8fd`
- `e9630d75-d783-4de0-969d-ce10e193a731`
- `6381b1f7-6b73-4e86-b2dd-581176be357d`

governance_alerts:
- `ce39ff60-1e38-4616-b114-959aa3122df3`
- `6928edc0-1e30-4a4d-9915-e0272172af28`
- `d48dc217-5027-4406-9c75-e9dd3ce050dd`

regulatory_updates:
- `01110dcd-34e6-4ffc-bef1-354d721a107b`

files:
- `/app/policies/updates/synthetic_measurement_credit_review.processed`

The `.txt` file was renamed to `.processed` by the agent; that processed file was removed. Existing registry systems, alerts, snapshots, audits and tasks were not edited.

## Governance Q&A

Grading rule: correct requires both the requested fact and any requested explanation; partly correct means supported content but an incomplete answer; wrong means contradictory/unsupported substantive answer. An unexecuted question is NOT COMPLETED.

| Question | Expected | Returned | Grade |
|---|---|---|---|
| 1: high-risk systems | credit only | credit only; fraud/spam minimal | Correct |
| 2: unresolved critical systems | credit and fraud | lists alert types, cannot identify systems | Partly correct |
| 3: spam tier and why | MINIMAL_RISK, excluded regulatory categories | correct tier and purpose, no regulatory rationale | Partly correct |
| 4: credit open-alert count | 3 | no request, Q&A call cap | NOT COMPLETED |
| 5: Article 14 | grounded oversight answer with citation | no request, Q&A call cap; offline retrieval precheck failed | NOT COMPLETED |
| 6: France capital | decline/out of scope | no request, Q&A call cap | NOT COMPLETED |

### Question 1

Which systems are high risk?

HTTP 200; 23.864 seconds. Provider/model: gemini / gemini-3.5-flash-lite; needs_review=False.

> Based on the provided list of AI systems, the system classified as high risk is the Credit Scoring Model v2 (credit_scoring_model-4dbb0f), which predicts the probability of loan default. The other systems, including the Fraud Detection Engine and the Email Spam Filter, are categorized as minimal risk.

Claimed sources: ["System Registry (3 systems)"]. Citations: []. Query type: registry_query.

Assessment: All factual statements match active registry tiers and purpose. No unsupported claim identified. Sources are a generic registry label, not row-level citations.

### Question 2

Which systems have unresolved critical alerts?

HTTP 200; 38.805 seconds. Provider/model: gemini / gemini-3.5-flash-lite; needs_review=False.

> There are multiple critical governance alerts recorded on 2026-10-06, specifically involving Equalized Odds Violations, Demographic Parity Violations, and Psi Violations. However, the provided alerts do not specify the names or identifiers of the individual systems experiencing these unresolved critical alerts.

Claimed sources: ["ARGUS Governance Alerts Database"]. Citations: []. Query type: alert_query.

Assessment: Alert types and date match stored rows. It does not answer which systems are affected. The prompt lacks resolved flags, so the claim that the supplied alerts are unresolved is not established by its prompt; the handler query can also include resolved rows. It honestly acknowledges missing system identifiers. Both the incompleteness and missing status context are application data-selection limitations, not invented system IDs.

### Question 3

What is the risk tier of the email spam filter, and why?

HTTP 200; 39.19 seconds. Provider/model: gemini / gemini-3.5-flash-lite; needs_review=False.

> The Email Spam Filter (email_spam_filter-c64b88) is classified as having a MINIMAL_RISK risk tier. It operates by classifying incoming email messages as spam or legitimate email for inbox filtering.

Claimed sources: ["System Registry (3 systems)"]. Citations: []. Query type: registry_query.

Assessment: Tier, ID and purpose match the registry. The answer does not explain the regulatory basis requested by "why"; stored classification reasoning was never sent in this handler prompt. No unsupported factual claim identified.

### Questions 4-6: UNVERIFIED

No requests were sent after reaching the six-live-call Q&A cap. Q4's ground truth is 3. For Q5, the offline similarity-retrieval precheck failed before any Q&A HTTP request/live call: `OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.` The environment was deliberately offline; the cached all-MiniLM-L6-v2 files were absent. No embedding-model download or retrieval change was attempted. Q1-3 are registry/alert handlers and do not use this model. Direct read-only SQL confirmed three indexed Article 14 chunks (page_number 60-61), but this is NOT proof of what similarity retrieval would send and no Q5 answer exists to compare. The indexed text requires effective human oversight, proportionate oversight measures, understanding limits, monitoring anomalies, awareness of automation bias, interpreting outputs, overriding decisions and safe interruption; the two-person verification rule is limited to the specified Annex III biometric-identification category and has stated exceptions. Q6 refusal behavior was not measured; source inspection alone shows no explicit scope guard.

## Actual Gemini usage metadata

All successful calls used gemini / gemini-3.5-flash-lite. Counts below are SDK usage metadata, not tokenizer estimates.

| Stage | Call | Input tokens | Output tokens | Status | Cache hit |
|---|---|---:|---:|---|---|
| Propagation | 1 | 410 | 138 | ok | False |
| Propagation | 2 | 316 | 18 | ok | False |
| Q&A | 1 | 179 | 15 | ok | False |
| Q&A | 2 | 448 | 79 | ok | False |
| Q&A | 3 | 180 | 15 | ok | False |
| Q&A | 4 | 461 | 70 | ok | False |
| Q&A | 5 | 187 | 15 | ok | False |
| Q&A | 6 | 456 | 62 | ok | False |

Total live calls: 8 (propagation 2, Q&A 6); input tokens 2637; output tokens 412; cache hits 0; 429/quota errors 0. No provider/auth/model errors or schema retries during live generation. Q&A stopped at its stage cap. Temporary HTTP listener stopped=True.

No Docker build, commits or application-source edits. No tests were run in this measurement task. Persistent changes: this report only; secret-free cache and usage logs are gitignored. Questions 4-6 and port-8000 resident-process Q&A behavior are UNVERIFIED.

Final checks: temporary port-8001 listener confirmed closed; synthetic .txt and .processed files confirmed absent; the running API still returns exactly the same six pre-existing open alert IDs. Temporary measurement scripts/results were removed.
