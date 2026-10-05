# Fixed labelled evaluation

Run status: complete. Completed 10/10 cases.
Tier accuracy: 9/10.
Strict provision matches (raw article string): 2/10.
Canonicalized provision matches (explicit fields, no inferred Article 5 paragraph): 6/10.
Clear-case accuracy: 7/8; 8 clear cases evaluated.
Unevaluated cases are UNVERIFIED and are not counted as incorrect predictions.
Provision identity matches: 6/10.
Needs review: 10 cases; IDs [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].
Provision matching includes checked exclusions. Article paragraph/subparagraph labels must match explicitly; prose mentions do not count. Scope/exception qualifiers require reading the reasoning and are not separately validated.
Grounding checks provision identity, not whether the interpretation or quoted excerpt is correct. Empty citation sets pass the identity check vacuously.

| ID | Name | Difficulty | Expected tier | Predicted tier | Expected provision | Supporting citations | Exclusions checked | Strict | Canonicalized | Grounded | Citation incomplete | Needs review / reasons | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Mortgage Affordability Scorer | clear | HIGH_RISK | HIGH_RISK | Annex III 5(b) | Annex III point 5(b), Article 6 | Article 5, Annex III point 1(b) | False | True | True | True | True / incomplete_citation | 0.98 |
| 2 | Video Interview Ranker | clear | HIGH_RISK | HIGH_RISK | Annex III 4(a) | Annex III point 4(a) | Article 5 | False | True | True | True | True / incomplete_citation | 0.98 |
| 3 | Phone Assistant | clear | LIMITED_RISK | LIMITED_RISK | Article 50(1) | Article 50 | Annex III point 5(d), Article 5 | False | False | True | True | True / incomplete_citation | 0.85 |
| 4 | Inventory Demand Forecaster | clear | MINIMAL_RISK | MINIMAL_RISK | none | none | Article 5, Annex III point 4 | True | True | True | True | True / incomplete_citation | 0.95 |
| 5 | Elderly Product Targeting Engine | clear | PROHIBITED | MINIMAL_RISK | Article 5(1)(b) | none | Article 5, Article 3 | False | False | True | True | True / incomplete_citation | 0.85 |
| 6 | Coursework Auto-Grader | clear | HIGH_RISK | HIGH_RISK | Annex III 3(b) | Annex III point 3(b) | Article 5 | False | True | True | True | True / incomplete_citation | 0.95 |
| 7 | Audiobook Voice Generator | ambiguous | LIMITED_RISK | LIMITED_RISK | Article 50(2) | Article 50 | Article 5, Annex III point 5(b) | False | False | True | True | True / incomplete_citation | 0.92 |
| 8 | Telecom Churn Predictor | clear | MINIMAL_RISK | MINIMAL_RISK | none | none | Article 5, Article 5 | True | True | True | True | True / incomplete_citation | 0.89 |
| 9 | Classroom Emotion Monitor | clear | PROHIBITED | PROHIBITED | Article 5(1)(f) | Article 5 | none | False | False | True | True | True / tier_citation_inconsistent:prohibited_without_article_5_paragraph, incomplete_citation | 0.99 |
| 10 | Credit Limit Assigner | ambiguous | HIGH_RISK | HIGH_RISK | Annex III 5(b) | Annex III point 5(b) | Article 5 | False | True | True | True | True / incomplete_citation | 0.95 |

## Confusion matrix (all cases, expected rows / predicted columns)

| Expected | PROHIBITED | HIGH_RISK | LIMITED_RISK | MINIMAL_RISK | UNCLASSIFIED |
|---|---|---|---|---|---|
| PROHIBITED | 1 | 0 | 0 | 1 | 0 |
| HIGH_RISK | 0 | 4 | 0 | 0 | 0 |
| LIMITED_RISK | 0 | 0 | 2 | 0 | 0 |
| MINIMAL_RISK | 0 | 0 | 0 | 2 | 0 |

## Wrong, incomplete and ambiguous cases: model reasoning

### 1: Mortgage Affordability Scorer

Expected HIGH_RISK; predicted HIGH_RISK; confidence 0.98.

> Step 1 analysis: The system does not match any prohibited practices under Article 5 such as social scoring, real-time biometric surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: The AI system evaluates whether mortgage applicants can afford repayments using financial data to produce an approval recommendation. This falls squarely under Annex III, point 5(b) as an AI system intended to be used to evaluate the creditworthiness of natural persons or establish their credit score, making it a high-risk AI system under Article 6.

### 2: Video Interview Ranker

Expected HIGH_RISK; predicted HIGH_RISK; confidence 0.98.

> Step 1 analysis: The system does not fall under prohibited practices outlined in Article 5 such as social scoring, real-time biometric mass surveillance, or subliminal manipulation. Step 2 analysis: The AI system is designed to analyze recorded video interviews of job candidates and rank them for recruiters based on speech and answer content. This directly corresponds to Annex III, point 4(a), which classifies AI systems intended to be used for the recruitment or selection of natural persons—specifically to evaluate candidates—as high-risk.

### 3: Phone Assistant

Expected LIMITED_RISK; predicted LIMITED_RISK; confidence 0.85.

> Step 1 analysis: The phone assistant does not engage in prohibited practices under Article 5 such as social scoring, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: The system does not fall under any high-risk categories listed in Annex III, such as critical infrastructure, high-risk employment tools, or emergency call evaluation/dispatch under Annex III point 5(d). Step 3 analysis: The system is an AI-enabled conversational system (phone assistant) interacting directly with natural persons to answer routine questions, which places it under LIMITED_RISK requiring transparency obligations pursuant to Article 50.

### 4: Inventory Demand Forecaster

Expected MINIMAL_RISK; predicted MINIMAL_RISK; confidence 0.95.

> Step 1 analysis: The inventory demand forecaster does not engage in prohibited practices such as subliminal manipulation or exploitation of vulnerabilities under Article 5. Step 2 analysis: It is used exclusively for warehouse stock planning based on historical sales and seasonality, meaning it does not fall under any of the high-risk categories in Annex III (such as critical infrastructure, education, employment, essential services, law enforcement, migration, or justice). Step 3 analysis: It is not a conversational system, emotion recognition system, AI-generated media tool, or human-interactive recommendation system, so it is not limited risk. Step 4 analysis: Therefore, by default, the system is classified as MINIMAL_RISK.

### 5: Elderly Product Targeting Engine

Expected PROHIBITED; predicted MINIMAL_RISK; confidence 0.85.

> Step 1 analysis: The system does not fall under any prohibited practices in Article 5, such as biometric mass surveillance, subliminal manipulation based on prohibited vulnerabilities, or social scoring. Step 2 analysis: The system tailors sales messages to elderly customers to sell expensive financial products, but it does not qualify as an AI system intended for credit scoring, insurance underwriting, or other high-risk categories under Annex III. Step 3 analysis: It is not a chatbot, emotion recognition system, deep fake generator, or biometric categorization system as defined in Article 3. Step 4 analysis: Since it does not meet the criteria for prohibited, high-risk, or limited-risk tiers based on the provided text, it defaults to MINIMAL_RISK.

### 6: Coursework Auto-Grader

Expected HIGH_RISK; predicted HIGH_RISK; confidence 0.95.

> Step 1 analysis: The system does not fall under prohibited practices in Article 5 such as social scoring, real-time biometric surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: The AI system is used for automatically grading university students' written coursework and recording results as part of assessed learning outcomes. This falls directly under Annex III, point 3(b) as an AI system intended to be used to evaluate learning outcomes in educational and vocational training institutions at all levels, making it HIGH_RISK.

### 7: Audiobook Voice Generator

Expected LIMITED_RISK; predicted LIMITED_RISK; confidence 0.92.

> Step 1 analysis: The system does not engage in prohibited practices under Article 5 such as social scoring, real-time biometric surveillance, or manipulative techniques. Step 2 analysis: The system is an audiobook voice generator used for narrating book text, which does not fall under any high-risk categories listed in Annex III such as critical infrastructure, education, employment, or credit scoring. Step 3 analysis: The system generates audio content which constitutes a deep fake or artificially generated audio under Article 50, triggering transparency obligations unless it forms part of an evidently artistic, creative, fictional or analogous work or programme. Step 4 analysis: Since transparency rules apply to generated audio content, it is classified as LIMITED_RISK.

### 8: Telecom Churn Predictor

Expected MINIMAL_RISK; predicted MINIMAL_RISK; confidence 0.89.

> Step 1 analysis: The system does not fall under any prohibited practices of Article 5 such as social scoring, biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: The system is a telecom churn predictor used to identify subscribers likely to cancel their plans, which does not match any high-risk use cases in Annex III (such as critical infrastructure, education, employment, essential services like credit scoring, law enforcement, migration, or administration of justice). Step 3 analysis: It is not a chatbot, emotion recognition system, AI-generated media tool, or recommendation system requiring specific transparency under Article 50. Step 4 analysis: Since it does not meet the criteria for prohibited, high-risk, or limited-risk categories, it defaults to minimal risk.

### 9: Classroom Emotion Monitor

Expected PROHIBITED; predicted PROHIBITED; confidence 0.99.

> Step 1 analysis: The system uses classroom cameras to infer pupils' emotions such as boredom or frustration in educational institutions. Under Article 5(1)(f), the placing on the market, putting into service, or use of AI systems to infer emotions of a natural person in the areas of workplace and education institutions is explicitly prohibited, except for medical or safety reasons. Since this system monitors general classroom emotions rather than functioning strictly for medical or safety reasons, it falls directly under prohibited practices.

### 10: Credit Limit Assigner

Expected HIGH_RISK; predicted HIGH_RISK; confidence 0.95.

> Step 1 analysis: The system does not fall under any prohibited practices listed in Article 5 such as social scoring or subliminal manipulation. Step 2 analysis: The system is designed to assign initial credit limits based on financial profiles and spending behaviour, which directly corresponds to evaluating the creditworthiness of natural persons under Annex III, point 5(b). Therefore, it is classified as HIGH_RISK.


## Not completed

[]

## Usage and cleanup

{
  "live_calls": 20,
  "input_tokens": 46859,
  "output_tokens": 6816,
  "cache_hits": 0,
  "quota_or_429_errors": 0,
  "statuses": [
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok",
    "ok"
  ]
}

DELETE endpoint results: [{"system_id": "eval_20a167fe_01_mor-dd64cd", "status": 204}, {"system_id": "eval_20a167fe_02_vid-5f93a3", "status": 204}, {"system_id": "eval_20a167fe_03_pho-076bde", "status": 204}, {"system_id": "eval_20a167fe_04_inv-39b1a4", "status": 204}, {"system_id": "eval_20a167fe_05_eld-b7c163", "status": 204}, {"system_id": "eval_20a167fe_06_cou-10a673", "status": 204}, {"system_id": "eval_20a167fe_07_aud-ed1c4e", "status": 204}, {"system_id": "eval_20a167fe_08_tel-bf7eb3", "status": 204}, {"system_id": "eval_20a167fe_09_cla-31b31a", "status": 204}, {"system_id": "eval_20a167fe_10_cre-1731f5", "status": 204}]

Stop reason: none

## Frozen input hashes

{
  "argus/config.py": "fc4259082c20e3843b9140a9ff2c48f5e9049159ea44b4756d51f02b1f347255",
  "argus/core/agents/registrar.py": "30a88717f68eb0ead7f39bd14c927180e28fb7c3760838ab5d4e5af986e15043",
  "argus/core/agents/risk_classifier.py": "43251f7b99d2f8d738cf37bff60bd9bc7ecaa156e7c6f042289d678330affc4f",
  "argus/core/llm.py": "422ec3baffcb0d949e235a1ada598e619de2542313a83574caef492f76a2ae4e",
  "argus/core/llm_schemas.py": "2e8a4bc715e68ae3c12f186daf0030e4314729ab02554a3f5f6299bf874ac0f7",
  "argus/rag/retriever.py": "ddf024f5430113e0aa9923f9e06efd3081371f7e1fce2042522bf02d4a7375d3",
  "argus/core/agents/drift_monitor.py": "458756e7ed8cebc8ed7ae74f15541602f0981ce78fa07e30d23aa7f9cbd270cd",
  "tests\\fixtures\\heldout_set.json": "083d57d2b922bf5075bd3cc48fefbf71eaf41d595ff7fca4f01fdba1700c6a16",
  "argus/core/citations.py": "b63965f29cdd4a5ef02ad05d5e780c579cd9394f3512d69f5d644d35a89cbb22",
  "scripts/run_labelled_eval.py": "f92bd6cd8204ade57c3e4b109c44727d59337ef5c5a5c67e991025658f062523"
}

## Measurement definitions and post-run checks

Strict provision matching compares the owner label exactly and case-sensitively with each raw citation.article string. Canonical matching projects explicit article/annex/point fields and compares canonical strings, refusing incomplete citations; it does not infer an omitted Article 5 paragraph. Non-none labels search supporting citations and checked exclusions; expected none requires no supporting citations.

All ten cases completed once over HTTP with EU jurisdiction only. No cases were rerun. All outputs used gemini / gemini-3.5-flash-lite. No prompts, thresholds, labels or canonicalization rules were changed after results arrived. The held-out-set SHA256 remains 083d57d2b922bf5075bd3cc48fefbf71eaf41d595ff7fca4f01fdba1700c6a16.

Review fired on all ten cases because each had an incomplete Article 5 identity, usually in exclusions_checked. Case 9 additionally has tier_citation_inconsistent:prohibited_without_article_5_paragraph. These flags concern structured identity completeness, not an independent legal assessment.

The preflight purpose-only Article 5 pin for case 5 was chunk 0 containing 1(b). In the actual run the Registrar inferred other / binary_classification, and the classifier's existing query appended those types, selecting chunk 2 instead. That context does not contain 1(b). Case 9 selected chunk 2 in both preflight and live context and contains 1(f). No corrective tuning was applied. Preflight details: [heldout_preflight_report.md](heldout_preflight_report.md).

Cleanup: ten DELETE endpoint responses were 204; database verification found zero active and ten inactive evaluation records for this run. The report and results passed a private exact-key scan without printing or writing the key.

Usage: 20 logged live calls, 46,859 input tokens, 6,816 output tokens, zero cache hits, zero quota/429 errors; all 20 statuses were ok. Nothing was retried. This stayed within the hard cap of 24.

UNVERIFIED: citation excerpt truth and legal interpretation were not independently validated. Grounded means the provision identity was present in retrieved metadata; article paragraph text is not separately checked by the existing grounding validator.

Final validation: one backend rebuild completed in under a minute, reusing CPU-only torch dependency layers. Plain pytest -q in the rebuilt image with API keys disabled: 82 passed, four deprecation warnings. No commit or push was performed.
Docker Compose is down; postgres_data and prometheus_data volumes are present.
