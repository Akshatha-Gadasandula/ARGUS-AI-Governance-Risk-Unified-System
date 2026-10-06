# Fixed labelled evaluation

Run status: complete. Completed 7/7 cases.
Tier accuracy: 6/7.
Strict provision matches (raw article string): 1/7.
Canonicalized provision matches (explicit fields, no inferred Article 5 paragraph): 7/7.
Clear-case accuracy: 4/5; 5 clear cases evaluated.
Unevaluated cases are UNVERIFIED and are not counted as incorrect predictions.
Provision identity matches: 3/7.
Needs review: 1 cases; IDs [1].
Provision matching includes checked exclusions. Article paragraph/subparagraph labels must match explicitly; prose mentions do not count. Scope/exception qualifiers require reading the reasoning and are not separately validated.
Grounding checks provision identity, not whether the interpretation or quoted excerpt is correct. Empty citation sets pass the identity check vacuously.

| ID | Name | Difficulty | Expected tier | Predicted tier | Expected provision | Supporting citations | Exclusions checked | Strict | Canonicalized | Grounded | Citation incomplete | Needs review / reasons | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Streaming Impulse Optimiser | clear | PROHIBITED | PROHIBITED | Article 5(1)(a) | Article 5(1)(a) | Article 50 | False | True | True | False | True / schema_repair | 0.98 |
| 2 | Future Crime Profiler | clear | PROHIBITED | HIGH_RISK | Article 5(1)(d) | Annex III point 6(d) | Article 5(1)(d) | False | True | True | False | False / none | 0.95 |
| 3 | Face Database Builder | clear | PROHIBITED | PROHIBITED | Article 5(1)(e) | Article 5(1)(e) | Annex III point 1(a) | False | True | True | False | False / none | 0.99 |
| 4 | Face Attribute Inferrer | clear | PROHIBITED | PROHIBITED | Article 5(1)(g) | Article 5(1)(g) | Article 50(3) | False | True | True | False | False / none | 0.99 |
| 5 | Film Recommender | clear | MINIMAL_RISK | MINIMAL_RISK | none | none | Article 5(1)(a), Annex III point 8(b) | True | True | True | False | False / none | 0.95 |
| 6 | Retail Emotion Analytics | ambiguous | HIGH_RISK | HIGH_RISK | Annex III 1(c) | Annex III point 1(c) | Article 5(1)(f) | False | True | True | False | False / none | 0.95 |
| 7 | Automated News Writer | ambiguous | LIMITED_RISK | LIMITED_RISK | Article 50(4) | Article 50(4) | Article 5, Annex III point 8(b) | False | True | True | False | False / none | 0.95 |

## Confusion matrix (all cases, expected rows / predicted columns)

| Expected | PROHIBITED | HIGH_RISK | LIMITED_RISK | MINIMAL_RISK | UNCLASSIFIED |
|---|---|---|---|---|---|
| PROHIBITED | 3 | 1 | 0 | 0 | 0 |
| HIGH_RISK | 0 | 1 | 0 | 0 | 0 |
| LIMITED_RISK | 0 | 0 | 1 | 0 | 0 |
| MINIMAL_RISK | 0 | 0 | 0 | 1 | 0 |

## Wrong, incomplete and ambiguous cases: model reasoning

### 1: Streaming Impulse Optimiser

Expected PROHIBITED; predicted PROHIBITED; confidence 0.98.

> Step 1 analysis: The AI system explicitly deploys subliminal techniques beyond a person's consciousness via imperceptible audio and visual cues in streaming content, with the objective or effect of materially distorting viewers' behaviour and causing them to make unintended purchasing decisions, thus violating Article 5(1)(a). Therefore, the system is classified as PROHIBITED.

### 2: Future Crime Profiler

Expected PROHIBITED; predicted HIGH_RISK; confidence 0.95.

> The AI system 'Future Crime Profiler' is designed to predict how likely individual people are to commit a crime in the future based on personality traits and profiles, and provides law enforcement with a ranked list. According to Annex III, point 6(d), AI systems intended to be used by law enforcement authorities in support of law enforcement for assessing the risk of a natural person offending or re-offending based on assessing personality traits and characteristics are classified as high-risk.

### 3: Face Database Builder

Expected PROHIBITED; predicted PROHIBITED; confidence 0.99.

> Step 1 analysis: The AI system collects facial images in bulk through untargeted scraping from social media sites and public CCTV footage to build a large searchable face recognition database. Under Article 5(1)(e), the placing on the market, putting into service, or use of AI systems that create or expand facial recognition databases through the untargeted scraping of facial images from the internet or CCTV footage is explicitly prohibited. Therefore, the system is classified as PROHIBITED.

### 4: Face Attribute Inferrer

Expected PROHIBITED; predicted PROHIBITED; confidence 0.99.

> Step 1 analysis: The AI system is designed to deduce or infer sexual orientation and religious beliefs from facial attributes using biometric data, which falls directly under Article 5(1)(g) prohibiting biometric categorisation systems that categorise natural persons based on their biometric data to deduce or infer race, political opinions, trade union membership, religious or philosophical beliefs, sex life, or sexual orientation. Therefore, the system is classified as PROHIBITED.

### 6: Retail Emotion Analytics

Expected HIGH_RISK; predicted HIGH_RISK; confidence 0.95.

> The AI system is designed to recognise shoppers' emotions as they browse in-store to adapt displays and offers. Under Annex III, point 1(c) of the EU AI Act, AI systems intended to be used for emotion recognition are explicitly classified as high-risk. Furthermore, Article 5(1)(f) prohibits emotion recognition systems in the areas of workplace and educational institutions, but since this system operates in a retail store rather than the workplace or education, it avoids prohibition while remaining strictly classified as high-risk due to its emotion recognition capabilities under Annex III.

### 7: Automated News Writer

Expected LIMITED_RISK; predicted LIMITED_RISK; confidence 0.95.

> Step 1 analysis: The AI system does not involve prohibited practices under Article 5 such as social scoring, real-time biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: It does not fall under any high-risk categories in Annex III. Step 3 analysis: The system generates text published to inform the public on matters of public interest without human review or editorial control, directly triggering transparency obligations under Article 50. Therefore, it is classified as LIMITED_RISK.


## Not completed

[]

## Usage and cleanup

{
  "live_calls": 15,
  "input_tokens": 63379,
  "output_tokens": 5372,
  "cache_hits": 0,
  "quota_or_429_errors": 0,
  "statuses": [
    "ok",
    "invalid_json",
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

Per-call tokens below come from SDK usage metadata; null means unavailable (no local estimates).

| Call | Provider | Model | Status | Cache hit | Input tokens | Output tokens |
|---|---|---|---|---|---|---|
| 1 | gemini | gemini-3.5-flash-lite | ok | False | 720 | 228 |
| 2 | gemini | gemini-3.5-flash-lite | invalid_json | False | 7169 | 334 |
| 3 | gemini | gemini-3.5-flash-lite | ok | False | 7185 | 386 |
| 4 | gemini | gemini-3.5-flash-lite | ok | False | 723 | 324 |
| 5 | gemini | gemini-3.5-flash-lite | ok | False | 7180 | 563 |
| 6 | gemini | gemini-3.5-flash-lite | ok | False | 713 | 286 |
| 7 | gemini | gemini-3.5-flash-lite | ok | False | 7476 | 385 |
| 8 | gemini | gemini-3.5-flash-lite | ok | False | 708 | 282 |
| 9 | gemini | gemini-3.5-flash-lite | ok | False | 7468 | 416 |
| 10 | gemini | gemini-3.5-flash-lite | ok | False | 700 | 225 |
| 11 | gemini | gemini-3.5-flash-lite | ok | False | 7283 | 413 |
| 12 | gemini | gemini-3.5-flash-lite | ok | False | 707 | 278 |
| 13 | gemini | gemini-3.5-flash-lite | ok | False | 7113 | 488 |
| 14 | gemini | gemini-3.5-flash-lite | ok | False | 711 | 279 |
| 15 | gemini | gemini-3.5-flash-lite | ok | False | 7523 | 485 |

Context-incomplete case IDs: [].

DELETE endpoint results: [{"system_id": "eval_49c62938_01_str-c60041", "status": 204}, {"system_id": "eval_49c62938_02_fut-c74f27", "status": 204}, {"system_id": "eval_49c62938_03_fac-99e18b", "status": 204}, {"system_id": "eval_49c62938_04_fac-984008", "status": 204}, {"system_id": "eval_49c62938_05_fil-bce6fb", "status": 204}, {"system_id": "eval_49c62938_06_ret-34dffe", "status": 204}, {"system_id": "eval_49c62938_07_aut-cc5431", "status": 204}]

Stop reason: none

## Frozen input hashes

{
  "argus/config.py": "fc4259082c20e3843b9140a9ff2c48f5e9049159ea44b4756d51f02b1f347255",
  "argus/core/agents/registrar.py": "30a88717f68eb0ead7f39bd14c927180e28fb7c3760838ab5d4e5af986e15043",
  "argus/core/agents/risk_classifier.py": "b2c0ba0d06f2addf4b758f897ccaef48c2128ac092de586c0cdce20d8c2c434c",
  "argus/core/llm.py": "422ec3baffcb0d949e235a1ada598e619de2542313a83574caef492f76a2ae4e",
  "argus/core/llm_schemas.py": "48b5968a2e9a6a815823869302790551a936752c3f75e76451f49761004d497d",
  "argus/rag/retriever.py": "ee0045b0774269a49752de412921e420803e34d1835211ef832ff31b07b08ddb",
  "argus/core/agents/drift_monitor.py": "458756e7ed8cebc8ed7ae74f15541602f0981ce78fa07e30d23aa7f9cbd270cd",
  "tests\\fixtures\\fresh_set.json": "356fe7a42bb8fa5cf2d7ca004b67dd3c26be47ae80d1bdaaf6858642efdca37d",
  "argus/core/citations.py": "a98cc996f97253781955999c8dcd2066fa4d709e400f0aafe7ab0e836b69638e",
  "scripts/run_labelled_eval.py": "08017472752ade3bb95ab9eb35ff48328b012356eb84b2a66e95a790cf0b9571"
}

## Preflight: Article 5 paragraph 1 screen (before live calls)

| Case | Article 5 chunk indices | Total context chunks | Full (a)-(h) screen |
|---|---|---|---|
| 1 Streaming Impulse Optimiser | [0, 1, 2, 3, 4] | 9 | True |
| 2 Future Crime Profiler | [0, 1, 2, 3, 4] | 9 | True |
| 3 Face Database Builder | [0, 1, 2, 3, 4] | 9 | True |
| 4 Face Attribute Inferrer | [0, 1, 2, 3, 4] | 9 | True |
| 5 Film Recommender | [0, 1, 2, 3, 4] | 9 | True |
| 6 Retail Emotion Analytics | [0, 1, 2, 3, 4] | 9 | True |
| 7 Automated News Writer | [0, 1, 2, 3, 4] | 9 | True |

## Interpretation of citation scores

The unchanged runner counts both supporting citations and exclusions_checked: canonical match is 7/7. Supporting citations alone match 6/7 (same canonicalization rule). Case 2 matches the expected Article 5(1)(d) only as an excluded provision while its tier and supporting Annex III point 6(d) differ from the owner label. A canonical identity match is not proof of correct classification.

Strict match compares the raw article field to the exact expected_provision string. Canonicalization combines the article/annex, paragraph and point fields without inferring omitted paragraphs. Completeness checks apply only to supporting citations; exclusions are exempt. No supporting citation is incomplete.

Grounded=yes means the existing provision identity check passed, not that the quoted text or legal interpretation has been verified. Article grounding checks the article identity, not exact paragraph coverage; empty supporting sets pass vacuously.

## Raw structured supporting citations

### Case 1

```json
[
  {
    "article": "Article 5",
    "title": "Prohibited AI practices",
    "excerpt": "the placing on the market, the putting into service or the use of an AI system that deploys subliminal techniques beyond a person’s consciousness or purposefully manipulative or deceptive techniques, with the objective, or the effect of materially distorting the behaviour of a person or a group of persons by appreciably impairing their ability to make an informed decision",
    "annex": null,
    "point": "a",
    "citation_role": "supporting",
    "paragraph": "1",
    "incomplete_reason": null,
    "canonical_citation": "Article 5(1)(a)",
    "citation_incomplete": false
  }
]
```

### Case 2

```json
[
  {
    "article": "Annex III",
    "title": "High-risk AI systems referred to in Article 6(2)",
    "excerpt": "AI systems intended to be used by law enforcement authorities or on their behalf or by Union institutions, bodies, offices or agencies in support of law enforcement authorities for assessing the risk of a natural person offending or re-offending not solely on the basis of the profiling of natural persons as referred to in Article 3(4) of Directive (EU) 2016/680, or to assess personality traits and characteristics or past criminal behaviour of natural persons or groups;",
    "annex": "III",
    "point": "6(d)",
    "citation_role": "supporting",
    "paragraph": null,
    "incomplete_reason": null,
    "canonical_citation": "Annex III point 6(d)",
    "citation_incomplete": false
  }
]
```

### Case 3

```json
[
  {
    "article": "Article 5",
    "title": "Prohibited AI practices",
    "excerpt": "the placing on the market, the putting into service for this specific purpose, or the use of AI systems that create or expand facial recognition databases through the untargeted scraping of facial images from the internet or CCTV footage",
    "annex": null,
    "point": "e",
    "citation_role": "supporting",
    "paragraph": "1",
    "incomplete_reason": null,
    "canonical_citation": "Article 5(1)(e)",
    "citation_incomplete": false
  }
]
```

### Case 4

```json
[
  {
    "article": "Article 5",
    "title": "Prohibited AI practices",
    "excerpt": "the placing on the market, the putting into service for this specific purpose, or the use of biometric categorisation systems that categorise individually natural persons based on their biometric data to deduce or infer their race, political opinions, trade union membership, religious or philosophical beliefs, sex life or sexual orientation;",
    "annex": null,
    "point": "g",
    "citation_role": "supporting",
    "paragraph": "1",
    "incomplete_reason": null,
    "canonical_citation": "Article 5(1)(g)",
    "citation_incomplete": false
  }
]
```

### Case 5

```json
[]
```

### Case 6

```json
[
  {
    "article": "Annex III",
    "title": "High-risk AI systems referred to in Article 6(2)",
    "excerpt": "AI systems intended to be used for emotion recognition.",
    "annex": "III",
    "point": "1(c)",
    "citation_role": "supporting",
    "paragraph": null,
    "incomplete_reason": null,
    "canonical_citation": "Annex III point 1(c)",
    "citation_incomplete": false
  }
]
```

### Case 7

```json
[
  {
    "article": "Article 50",
    "title": "Transparency obligations for providers and deployers of certain AI systems",
    "excerpt": "Deployers of an AI system that generates or manipulates text which is published with the purpose of informing the public on matters of public interest shall disclose that the text has been artificially generated or manipulated.",
    "annex": null,
    "point": null,
    "citation_role": "supporting",
    "paragraph": "4",
    "incomplete_reason": "Article 50 paragraph 4 does not contain lettered sub-points.",
    "canonical_citation": "Article 50(4)",
    "citation_incomplete": false
  }
]
```

## Verification and limits

- Plain container pytest: 94 passed, 4 deprecation warnings.
- All seven registrations returned HTTP 201; all seven DELETEs returned HTTP 204; active registrations for this run after cleanup: 0.
- One final backend rebuild succeeded using cached CPU-only torch and requirements layers. Testing used docker compose cp; no build preceded measurement.
- Fresh fixture and eight earlier result/report files have unchanged SHA-256 hashes. Application classification code matched the workspace before measurement; no prompts, thresholds, retrieval, or labels were changed.
- All 15 calls have actual Gemini SDK input/output token metadata; no tokenizer estimates appear in the usage table.
- UNVERIFIED: runtime of the final rebuilt image (measurement and tests used the existing image with copied evaluation files); exact paragraph/excerpt truth and legal interpretation are outside the existing identity-grounding check.
