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


---

# Q&A follow-up after diagnosed fixes (2026-10-06)

The earlier propagation/Q&A measurement above is preserved. This follow-up used all ten fixed questions once over the resident Docker API, POST http://localhost:8000/api/v1/qa/ask. No propagation run or regulatory data mutation was performed. Application code and prompts were finalized/tested before live calls and were not changed after live results.

## Exact pre-fix prompt inspection (zero live calls)

The first LLM call classified the question as registry_query, compliance_query, alert_query or general. It received the question/category descriptions, no database data. The second generated the answer. The following are the EXACT second-call prompt bodies captured from the existing container/database with generation mocked:

### Q2: unresolved critical alerts

```text
Given these recent governance alerts and the question, provide an answer:

RECENT ALERTS:
- [2026-10-06] CRITICAL: Equalized Odds Violation
- [2026-10-06] CRITICAL: Demographic Parity Violation
- [2026-10-06] CRITICAL: Psi Violation
- [2026-10-06] CRITICAL: Psi Violation
- [2026-10-06] CRITICAL: Psi Violation
- [2026-10-06] CRITICAL: Equalized Odds Violation
- [2026-10-06] CRITICAL: Demographic Parity Violation

QUESTION: Which systems have unresolved critical alerts?

Summarize the alert situation relevant to the question in 2-3 sentences.
```

### Q3: email spam tier and why

```text
Given this list of AI systems and the question, provide a helpful answer.

SYSTEMS:
- Credit Scoring Model v2 (credit_scoring_model-4dbb0f): Predicts probability of loan default using applicant transaction history, Risk: HIGH_RISK
- Fraud Detection Engine (fraud_detection_engi-2a6271): Classify financial transactions as fraudulent or legitimate using behavioral patterns and transactio, Risk: MINIMAL_RISK
- Email Spam Filter (email_spam_filter-c64b88): Classify incoming email messages as spam or legitimate email for inbox filtering, Risk: MINIMAL_RISK

QUESTION: What is the risk tier of the email spam filter, and why?

Provide a concise, helpful answer in 2-3 sentences. If specific system names are needed, use the system_id.
```

The shared layer additionally appends the JSON response schema and the instruction to cite only retrieved chunks; these two handler calls provided no chunks, so that appended context was `[]`. Q2 lacked system IDs/names, resolved flags, and a resolved=false SQL filter; it included seven rows, one already resolved. Q3 contained IDs/names, truncated purposes and tiers, but omitted stored classification reasoning, citations, original provider/model and needs_review/reasons. These omissions explain the previous incomplete answers.

## Changes finalized before live calls

- Removed LLM question classification and the generic mock-answer routes. Supported registry facts are deterministic SQL answers with row-level sources (including UUID, public ID, name, and relevant fields). Alert queries restrict to unresolved rows, apply severity when requested, and associate each alert with its active system. No provider lookup or outbound call occurs for deterministic or out-of-scope paths.
- System why answers pass the stored per-framework classification/reasoning/citations, provider/model and review flags to one shared-layer call. The returned answer also deterministically identifies the ORIGINAL tier provider/model; the answer-generation provider/model remain separate response fields. The response exposes stored_classification, row_sources and review reasons.
- Regulation answers use EU_AI_ACT retrieved text only, cite its provision, and return the literal `not found in the indexed text` without a call if retrieval is empty. Unsupported model citations are still dropped/flagged by the shared layer. The shared layer now accepts max_attempts; Q&A sets it to one. Other callers keep their existing four-attempt maximum. Q&A therefore has no invalid-JSON/quota retry; a quota response stops this measurement immediately, respecting the one-outbound-call maximum.
- Added huggingface_cache mounted at /root/.cache/huggingface. Only the backend was recreated with --no-build to attach the volume. Existing CPU-only torch requirements were untouched. Download completed, and offline loading verified dimension 384. No Docker image build was run.

Pre-live retrieval correction: the frozen fixture captured an initial generic top-five search followed by article filtering (Q5 zero retained chunks; Q10 one). That preflight exposed a routing bug before any live call. The final implementation applies the explicit Article N metadata filter BEFORE similarity search selects five results, for ANY requested article number; it does not change distance scoring or thresholds. Its mocked regression uses Article 37, not either measured article. Final pre-live context was 3 Article 14 and 4 Article 50 chunks. The fixture's original preflight snapshots were retained without editing; its complete indexed article texts are the database ground truth used below. Actual final contexts were saved separately in the measurement output and compared to those indexed records.

## Frozen question set and verification

`tests/fixtures/qa_questions.json` was generated programmatically from active AISystem records, unresolved GovernanceAlert records, stored classification fields and indexed article documents, BEFORE any live Gemini call. The scope-decline expectation comes from the application policy constant, not a manually typed geography answer. Questions 1-6 are regression checks; 7-10 are new questions. Labels/expectations/questions were not changed after freezing. No question was rerun.

Fixture SHA-256 before AND after:
`687cb517797de3100e82ab102db9a8a03fe63fdae9d7afa7fa78dd622e45415d`

All live-run source hashes also matched before/after. Frozen-fixture assertions verified exact matching system/alert source sets, open-alert counts, total active count, owner team and fixed decline behavior. Legal answers were additionally reviewed against the saved final retrieved text, not model memory.

Plain container pytest: **118 passed**, four existing/dependency deprecation warnings. Mocked cases cover deterministic counts/lists/owners/tiers/jurisdictions/open alerts, stored why context and original-provider attribution, grounded regulation generation, empty retrieval, Article N search filtering, decline, and one-attempt invalid-JSON/quota behavior. The first test run exposed a missing aiosqlite test dependency; tests now use built-in in-memory SQLite through a small async adapter, with no new package requirement. No suite was rerun after live results because application code did not change.

## Regression questions 1-6

Grading: correct means the requested fact/reason and material scope are supported; partly correct means supported core content with a material qualification/requirement omitted; wrong means a contradictory or unsupported core answer. This is manual legal-content grading against the fixed source text, not a new tier-labelled dataset.

| Q | Ground truth | Returned summary | Calls | Grade |
|---|---|---|---:|---|
| 1 | credit only HIGH_RISK | credit only, HIGH_RISK | 0 | Correct |
| 2 | credit and fraud have unresolved CRITICAL alerts | both named, six matching open critical row sources | 0 | Correct |
| 3 | spam MINIMAL_RISK; stored exclusions/reasoning; original gemini/model | correct tier, stored explanation and original attribution | 1 | Correct |
| 4 | credit has 3 open alerts | 3, with exact alert-row sources | 0 | Correct |
| 5 | Article 14 oversight duties, including scoped two-person rule/conditional exceptions | core duties correct; omitted precise scope and exception condition | 1 | Partly correct |
| 6 | decline out of scope | fixed decline; no sources | 0 | Correct |

Regression: **5 correct, 1 partly correct, 0 wrong**. Q1 remains correct; Q2 and Q3 improved from partly correct to correct. Prior Q4-6 had not completed; this run measures them.

## New questions 7-10

| Q | Ground truth | Returned summary | Calls | Grade |
|---|---|---|---:|---|
| 7 | 3 active registered systems | 3, with all three registry rows | 0 | Correct |
| 8 | fraud owner Financial Crime AI; email null | correct team; email not recorded | 0 | Correct |
| 9 | fraud and spam MINIMAL_RISK | both, with matching registry rows | 0 | Correct |
| 10 | Article 50(1) disclosure/exceptions plus 50(5) form/timing/accessibility | correct disclosure and paragraph-1 exceptions; omitted paragraph-5 requirements | 1 | Partly correct |

New questions: **3 correct, 1 partly correct, 0 wrong**. Combined: **8 correct, 2 partly correct, 0 wrong**. All ten completed with HTTP 200.

## Full per-question outputs, sources and unsupported-claim checks

### Q1: Which systems are high risk?

Calls: 0; HTTP 200; latency 0.098 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> Credit Scoring Model v2 (credit_scoring_model-4dbb0f): HIGH_RISK; jurisdictions EU

Sources:
- `ai_systems:9946dda9-bfa7-4265-b1ef-6b9e6dec3596 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`

Structured citations:
```json
[]
```

Assessment: Programmatic source-set match: only the stored HIGH_RISK system. No unsupported claim.

### Q2: Which systems have unresolved critical alerts?

Calls: 0; HTTP 200; latency 0.04 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> Systems with unresolved critical alerts: Credit Scoring Model v2 (credit_scoring_model-4dbb0f), Fraud Detection Engine (fraud_detection_engi-2a6271).

Sources:
- `governance_alerts:0fe18475-5f89-498a-96f9-22c9c0be5caf - Fraud Detection Engine (fraud_detection_engi-2a6271)`
- `governance_alerts:6e478d99-321b-425a-9ee2-8ee742d17bba - Fraud Detection Engine (fraud_detection_engi-2a6271)`
- `governance_alerts:9a4bb369-04b5-4451-85aa-692731c2b7ba - Fraud Detection Engine (fraud_detection_engi-2a6271)`
- `governance_alerts:a298697d-dccb-4c7d-b1c9-861b73bf9f47 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`
- `governance_alerts:c9941735-3511-4208-a049-d4c9590c64c6 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`
- `governance_alerts:dfaacefc-644a-4e1a-872e-8484bd31f4ca - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`

Structured citations:
```json
[]
```

Assessment: Programmatic exact alert-ID match, every returned source resolved=false and CRITICAL, both active systems correctly identified. No unsupported claim.

### Q3: What is the risk tier of the email spam filter, and why?

Calls: 1; HTTP 200; latency 3.213 seconds. Answer provider/model: gemini / gemini-3.5-flash-lite. needs_review=True; reasons=["dropped_citation"].

> Stored tier: MINIMAL_RISK. Original classification: EU_AI_ACT: MINIMAL_RISK, produced by gemini / gemini-3.5-flash-lite. The Email Spam Filter has been classified with a risk tier of MINIMAL_RISK under the EU_AI_ACT framework. The original tier was produced by the provider gemini, using the model gemini-3.5-flash-lite. The reasoning is that the system does not employ subliminal techniques, exploit vulnerable groups, perform social scoring, engage in biometric mass surveillance, or violate any prohibited practices under Article 5. It does not fall under any high-risk categories listed in Annex III. Furthermore, it is a standard NLP binary classification tool for spam filtering rather than a chatbot, emotion recognition system, AI-generated media, or recommendation system requiring transparency under Article 50, resulting in a default classification of MINIMAL_RISK.

Sources:
- `ai_systems:05f22075-74be-4bcf-aa68-9b234f979905 - Email Spam Filter (email_spam_filter-c64b88)`

Structured citations:
```json
[]
```

Assessment: Tier, explanation and original provider/model match the stored EU_AI_ACT classification. Its statements about excluded Article 5/Annex III/Article 50 categories reproduce stored reasoning; this is not a fresh statutory validation of that stored reasoning. The original stored needs_review was false, but answer-generation needs_review is true with dropped_citation: the model tried to supply citation identities not supported by the stored SUPPORTING citations, which are empty for this minimal-risk system. Unsupported structured citations were dropped, leaving the registry row as provenance. No additional unsupported textual claim relative to the stored context.

### Q4: How many open alerts does the credit scoring system have?

Calls: 0; HTTP 200; latency 0.028 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> Credit Scoring Model v2 (credit_scoring_model-4dbb0f): 3 open alerts.

Sources:
- `governance_alerts:a298697d-dccb-4c7d-b1c9-861b73bf9f47 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`
- `governance_alerts:c9941735-3511-4208-a049-d4c9590c64c6 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`
- `governance_alerts:dfaacefc-644a-4e1a-872e-8484bd31f4ca - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`
- `ai_systems:9946dda9-bfa7-4265-b1ef-6b9e6dec3596 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`

Structured citations:
```json
[]
```

Assessment: Count and exact alert IDs match the frozen unresolved database rows. No unsupported claim.

### Q5: What does Article 14 of the EU AI Act require?

Calls: 1; HTTP 200; latency 19.283 seconds. Answer provider/model: gemini / gemini-3.5-flash-lite. needs_review=False; reasons=[].

> Article 14 requires that high-risk AI systems be designed and developed with appropriate human-machine interface tools so they can be effectively overseen by natural persons while in use. Human oversight aims to prevent or minimize risks to health, safety, or fundamental rights. The oversight measures must be commensurate with the risks, level of autonomy, and context of use, and can be built into the system by the provider or implemented by the deployer. Additionally, the system must be provided to the deployer in a way that enables designated natural persons to understand its capacities and limitations, remain aware of automation bias, correctly interpret outputs, decide not to use or override outputs, and intervene or interrupt the system. For certain high-risk AI systems under Annex III, no action or decision can be taken by the deployer based on the system's identification unless separately verified and confirmed by at least two natural persons, with specific exceptions for law enforcement, migration, border control, or asylum.

Sources:
- `Article 14 - eu_ai_act.pdf, p. 61`
- `Article 14 - eu_ai_act.pdf, p. 60`

Structured citations:
```json
[
  {
    "article": "Article 14",
    "title": "Human oversight",
    "excerpt": "High-risk AI systems shall be designed and developed in such a way, including with appropriate human-machine interface tools, that they can be effectively overseen by natural persons during the period in which they are in use.",
    "annex": null,
    "point": null,
    "citation_role": "supporting"
  }
]
```

Assessment: Core oversight requirements are supported by all three retrieved Article 14 chunks (PDF pages 60-61). Material omissions: the two-person verification rule applies specifically to Annex III point 1(a), rather than an unnamed subset; its law-enforcement/migration/border/asylum exception requires Union or national law to consider two-person verification disproportionate. The answer says "For certain high-risk AI systems under Annex III" and "with specific exceptions for law enforcement, migration, border control, or asylum" without those qualifications. It does not invent a different rule, but cannot be read as supporting an automatic exception for those uses. Hence partly correct. No outright contradictory or extraneous claim; incompleteness is not detected by its needs_review=false flag.

### Q6: What is the capital of France?

Calls: 0; HTTP 200; latency 0.012 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> I can only answer questions about the ARGUS system registry, its governance alerts, and the indexed EU AI Act.

Sources:
- None.

Structured citations:
```json
[]
```

Assessment: Exact fixed decline policy match, no claimed sources, no generation call. No unsupported geography answer.

### Q7: How many AI systems are registered?

Calls: 0; HTTP 200; latency 0.023 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> 3 active AI systems are registered matching this query.

Sources:
- `ai_systems:9946dda9-bfa7-4265-b1ef-6b9e6dec3596 - Credit Scoring Model v2 (credit_scoring_model-4dbb0f)`
- `ai_systems:05f22075-74be-4bcf-aa68-9b234f979905 - Email Spam Filter (email_spam_filter-c64b88)`
- `ai_systems:01202f89-2807-45e6-b3d3-85824d4ae881 - Fraud Detection Engine (fraud_detection_engi-2a6271)`

Structured citations:
```json
[]
```

Assessment: Count and matching active-system source IDs agree with the database. No unsupported claim.

### Q8: Who owns the fraud detection system?

Calls: 0; HTTP 200; latency 0.018 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> Fraud Detection Engine (fraud_detection_engi-2a6271): owner team Financial Crime AI; owner email not recorded

Sources:
- `ai_systems:01202f89-2807-45e6-b3d3-85824d4ae881 - Fraud Detection Engine (fraud_detection_engi-2a6271)`

Structured citations:
```json
[]
```

Assessment: Owner team and absent owner email match the exact fraud row. No unsupported claim.

### Q9: Which systems are minimal risk?

Calls: 0; HTTP 200; latency 0.019 seconds. Answer provider/model: none / None. needs_review=False; reasons=[].

> Email Spam Filter (email_spam_filter-c64b88): MINIMAL_RISK; jurisdictions EU; Fraud Detection Engine (fraud_detection_engi-2a6271): MINIMAL_RISK; jurisdictions EU

Sources:
- `ai_systems:05f22075-74be-4bcf-aa68-9b234f979905 - Email Spam Filter (email_spam_filter-c64b88)`
- `ai_systems:01202f89-2807-45e6-b3d3-85824d4ae881 - Fraud Detection Engine (fraud_detection_engi-2a6271)`

Structured citations:
```json
[]
```

Assessment: Both and only MINIMAL_RISK active systems were returned. No unsupported claim.

### Q10: What does Article 50 require for AI systems that interact with people?

Calls: 1; HTTP 200; latency 20.29 seconds. Answer provider/model: gemini / gemini-3.5-flash-lite. needs_review=False; reasons=[].

> Article 50 requires providers to ensure that AI systems intended to interact directly with natural persons are designed and developed so that the natural persons are informed they are interacting with an AI system, unless this is obvious from the point of view of a reasonably well-informed, observant, and circumspect person considering the circumstances and context of use. This obligation does not apply to AI systems authorised by law to detect, prevent, investigate, or prosecute criminal offences, subject to appropriate safeguards, unless those systems are available for the public to report a criminal offence.

Sources:
- `Article 50 - eu_ai_act.pdf, p. 82`
- `Article 50 - eu_ai_act.pdf, p. 83`

Structured citations:
```json
[
  {
    "article": "Article 50",
    "title": "Transparency obligations for providers and deployers of certain AI systems",
    "excerpt": "Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system, unless this is obvious from the point of view of a natural person who is reasonably well-informed, observant and circumspect, taking into account the circumstances and the context of use.",
    "annex": null,
    "point": "1",
    "citation_role": "supporting"
  }
]
```

Assessment: Disclosure and obvious-interaction/criminal-offence/public-reporting qualifications are supported by retrieved Article 50(1). Paragraph 50(5), also in retrieved context, additionally requires clear/distinguishable information at the latest at first interaction/exposure, conforming to accessibility requirements. These material form/timing/accessibility duties were omitted; hence partly correct. No unsupported extra claim. needs_review=false did not detect this omission. Raw citation article="Article 50", point="1"; the current Q&A Citation schema has no separate paragraph field, so this is not a canonical Article 50(1) identity.

## Actual per-call usage

Estimated 3 outbound calls; measured 3, within the hard cap of 16. All were gemini / gemini-3.5-flash-lite. Seven deterministic/scope answers made zero calls, including Q1/Q2/Q4/Q6/Q7/Q8/Q9. There were no auth, provider/model, quota or cap errors; no retries; no cache hits. Token counts are from the SDK usage metadata.

| Q | Calls | Input tokens | Output tokens | Status |
|---|---:|---:|---:|---|
| 1 | 0 | 0 | 0 | deterministic/declined |
| 2 | 0 | 0 | 0 | deterministic/declined |
| 3 | 1 | 2483 | 215 | ok |
| 4 | 0 | 0 | 0 | deterministic/declined |
| 5 | 1 | 1535 | 298 | ok |
| 6 | 0 | 0 | 0 | deterministic/declined |
| 7 | 0 | 0 | 0 | deterministic/declined |
| 8 | 0 | 0 | 0 | deterministic/declined |
| 9 | 0 | 0 | 0 | deterministic/declined |
| 10 | 1 | 2056 | 267 | ok |

Total SDK input tokens: 6074; output tokens: 780. needs_review fired on Q3 only (dropped citation); it did not flag Q5/Q10's material omissions.

## Cache persistence and rebuild commands

Named volume: argus_huggingface_cache, mounted at /root/.cache/huggingface. Online population and a separate offline CPU load both succeeded (384 dimensions). The backend was restarted afterwards and used the cache for live regulation retrieval. No Docker build was run. Rebuilds themselves remain UNVERIFIED.

From the nested argus folder, rebuild/install the final code:

```powershell
docker compose build backend
docker compose up -d --no-deps backend
```

No dashboard changes or rebuild are needed. Verify persistence after a recreate without rebuilding:

```powershell
docker compose up -d --no-build --no-deps --force-recreate backend
docker compose exec -T -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 backend python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu'); print(m.get_sentence_embedding_dimension())"
```

Expected: 384 with network disabled. Inspect only mounts with `docker inspect argus-backend --format '{{json .Mounts}}'` and verify Type=volume, Name=argus_huggingface_cache, Destination=/root/.cache/huggingface. Never use `docker compose down -v` when preserving the model cache. The recreate command replaces copied source files with image contents, so run it after rebuilding to keep the final Q&A code.

UNVERIFIED: image rebuild, persistence across an actual rebuild (named volume configuration and offline load verified), arbitrary phrasings beyond supported deterministic routing patterns, exhaustive legal coverage of generated summaries, and browser behavior. No application code/prompts/thresholds or frozen fixture was changed after live results. No database rows were created or edited by the Q&A run; only the shared cache/usage log received its normal gitignored entries.
