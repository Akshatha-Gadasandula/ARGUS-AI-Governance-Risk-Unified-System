# Provision checks: strict score is primary

**Strict provision match: 2/15.** Clear cases: 2/13.
Normalized provision match: 11/15. Clear cases: 9/13.
Cases where strict and normalized differ: [1, 2, 6, 7, 8, 9, 12, 14, 15].

Exact, case-sensitive equality between the owner's expected_provision string and a returned citation.article string. No field joining or spelling/punctuation changes. For 'none', no supporting citations.

Canonical own-identity projection: parse the expected string and each returned citation's article/annex/point fields into article-or-annex, number/id, paragraph/point and subparagraph. Ignore case, whitespace, commas, the word 'point', and the expected-label qualifiers 'fraud exception'/'scope'. Combine separately supplied identity fields. Only for Article 5, a lone letter has implicit paragraph 1: 5(f) = 5(1)(f). Never infer a clause from a title, excerpt, reasoning, or expected answer; a bare Article 5 remains underspecified. For expected 'none', both scores require an empty supporting-citation list; checked exclusions are allowed. Non-none matching searches supporting citations and checked exclusions alike. This is a single identity-projection rule applied uniformly, not a validation of scope or legal interpretation.

The original recorded case objects, original runner scores, labels, prompts, thresholds and retrieval are preserved. The scores below are a separate post-run analysis.

| ID | Expected provision | Strict | Normalized | Failure classification |
|---|---|---|---|---|
| 1 | Annex III 5(b) | False | True | formatting mismatch |
| 2 | Annex III 4(a) | False | True | formatting mismatch |
| 3 | none | True | True | none |
| 4 | Article 50(1) | False | False | genuinely different or missing provision |
| 5 | Article 5(1)(c) | False | False | formatting / missing structured clause specificity |
| 6 | Annex III 5(b) fraud exception | False | True | formatting mismatch |
| 7 | Annex III 5(c) | False | True | formatting mismatch |
| 8 | Annex III 3(d) | False | True | formatting mismatch |
| 9 | Article 5(1)(f) | False | True | formatting mismatch |
| 10 | Article 50(4) | False | False | genuinely different or missing provision |
| 11 | none | True | True | none |
| 12 | Annex III 3(a) | False | True | formatting mismatch |
| 13 | none | False | False | genuinely different or missing provision |
| 14 | Annex III 4(b) | False | True | formatting mismatch |
| 15 | Annex III 5(b) scope | False | True | formatting mismatch |

## Failed strict checks: raw structured format and reasoning

### Case 1: Retail loan default predictor

Expected: Annex III 5(b). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score, with the exception of AI systems used for the purpose of detecting financial fraud;",
      "annex": "III",
      "point": "5(b)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for biometric categorisation, according to sensitive or protected attributes or characteristics based on the inference of those attributes or characteristics;",
      "annex": "III",
      "point": "1(b)",
      "citation_role": "exclusion_checked"
    },
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to evaluate learning outcomes, including when those outcomes are used to steer the learning process of natural persons in educational and vocational training institutions at all levels;",
      "annex": "III",
      "point": "3(b)",
      "citation_role": "exclusion_checked"
    },
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for the recruitment or selection of natural persons, in particular to place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates;",
      "annex": "III",
      "point": "4(a)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: The system is not prohibited under Article 5 as it does not engage in social scoring, real-time biometric surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: The AI system's purpose is to predict retail loan default probability using credit history, which directly matches Annex III, point 5(b) concerning AI systems intended to evaluate the creditworthiness of natural persons or establish their credit score. Therefore, it is classified as HIGH_RISK.

### Case 2: CV screening and applicant ranking

Expected: Annex III 4(a). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for the recruitment or selection of natural persons, in particular to place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates;",
      "annex": "III",
      "point": "4(a)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": []
}
```

Model reasoning:

> Step 1 analysis: The system does not fall under any prohibited practices pursuant to Article 5. Step 2 analysis: The AI system is designed for screening CVs and ranking applicants, which directly matches Annex III, point 4(a) regarding AI systems intended to be used for recruitment or selection of natural persons, including analysing and filtering job applications and evaluating candidates. Therefore, it is classified as HIGH_RISK.

### Case 4: Banking FAQ chatbot

Expected: Article 50(1). Failure: genuinely different or missing provision. No returned own identity matches the expected provision, or supporting citations were returned where none was expected.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Article 6",
      "title": "Classification rules for high-risk AI systems",
      "excerpt": "Classification rules for high-risk AI systems considered to be high-risk where it does not pose a significant risk of harm...",
      "annex": null,
      "point": null,
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score",
      "annex": "III",
      "point": "5(b)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> The AI system is a banking FAQ chatbot designed to answer routine customer service questions regarding opening hours, account features, and procedures. Based on Step 3 of the framework, AI-enabled conversational systems and chatbots are classified as LIMITED_RISK and are subject to specific transparency obligations. It does not engage in prohibited practices under Article 5 nor high-risk activities such as credit scoring under Annex III, point 5(b).

### Case 5: Public authority social scoring

Expected: Article 5(1)(c). Failure: formatting / missing structured clause specificity. The correct article/annex is named, but the required clause is absent from the identity fields; normalization cannot recover it.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Article 5",
      "title": "Prohibited AI practices",
      "excerpt": "the placing on the market, the putting into service or the use of AI systems for the evaluation or classification of natural persons or groups of persons over a certain period of time based on their social behaviour or known, inferred or predicted personal or personality characteristics, with the social score leading to either or both of the following: (i) detrimental or unfavourable treatment of certain natural persons or groups of persons in social contexts that are unrelated to the contexts in which the data was originally generated or collected; (ii) detrimental or unfavourable treatment of certain natural persons or groups of persons that is unjustified or disproportionate to their social behaviour or its gravity",
      "annex": null,
      "point": null,
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used by public authorities or on behalf of public authorities to evaluate the eligibility of natural persons for essential public assistance benefits and services",
      "annex": "III",
      "point": "5(a)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: The AI system evaluates citizens based on social behaviour and personal characteristics to determine access to public benefits and services, matching the prohibition under Article 5(c) regarding social scoring by public authorities leading to detrimental or unfavourable treatment. Step 2 analysis: High-risk and other tiers do not need to be applied because the system is directly prohibited under Article 5.

### Case 6: Card transaction fraud detector

Expected: Annex III 5(b) fraud exception. Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III, point 5(b)",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score, with the exception of AI systems used for the purpose of detecting financial fraud;",
      "annex": "III",
      "point": "5(b)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Article 5",
      "title": "Prohibited AI practices",
      "excerpt": "Prohibited practices checked and none found applicable to card transaction fraud detection.",
      "annex": null,
      "point": null,
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: The system does not engage in prohibited practices such as social scoring, biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups under Article 5. Step 2 analysis: While the system operates in the financial sector, Annex III Point 5(b) explicitly excludes AI systems used for the purpose of detecting financial fraud from being classified as high-risk credit scoring or creditworthiness evaluation systems. Step 3 analysis: The system is not a conversational chatbot, emotion recognition system, general-purpose AI-generated media tool, or a recommendation system requiring specific transparency obligations under the limited risk tiers. Step 4 analysis: Since it does not meet the criteria for prohibited, high-risk, or limited-risk tiers, the system defaults to MINIMAL_RISK.

### Case 7: Life and health insurance pricing

Expected: Annex III 5(c). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for risk assessment and pricing in relation to natural persons in the case of life and health insurance;",
      "annex": "III",
      "point": "5(c)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for biometric categorisation, according to sensitive or protected attributes or characteristics based on the inference of those attributes or characteristics;",
      "annex": "III",
      "point": "1(b)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: The system does not involve prohibited practices such as social scoring, real-time biometric surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: The AI system is intended to be used for risk assessment and pricing in relation to natural persons in the case of life and health insurance, which explicitly falls under Annex III, point 5(c) of the EU AI Act as a high-risk AI system.

### Case 8: Exam cheating detection

Expected: Annex III 3(d). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for monitoring and detecting prohibited behaviour of students during tests in the context of or within educational and vocational training institutions at all levels.",
      "annex": "III",
      "point": "3(d)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": []
}
```

Model reasoning:

> Step 1 analysis: The system is not prohibited under Article 5. Step 2 analysis: The AI system is intended to monitor students during examinations and detect behavior that may indicate cheating, which directly falls under Annex III, point 3(d) concerning AI systems used for monitoring and detecting prohibited behavior of students during tests within educational institutions.

### Case 9: Workplace employee emotion recognition

Expected: Article 5(1)(f). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Article 5",
      "title": "Prohibited AI practices",
      "excerpt": "the placing on the market, the putting into service for this specific purpose, or the use of AI systems to infer emotions of a natural person in the areas of workplace and education institutions, except where the use of the AI system is intended to be put in place or into the market for medical or safety reasons",
      "annex": null,
      "point": "f",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for emotion recognition",
      "annex": "III",
      "point": "1(c)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: The AI system is designed to infer emotions of natural persons from facial expressions and voice recordings in the workplace. Under Article 5(1)(f), the use of AI systems to infer emotions of a natural person in the areas of workplace and education institutions is explicitly prohibited, except for medical or safety reasons which do not apply here. Therefore, the system is classified as PROHIBITED.

### Case 10: Marketing deepfake image generator

Expected: Article 50(4). Failure: genuinely different or missing provision. No returned own identity matches the expected provision, or supporting citations were returned where none was expected.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Article 3",
      "title": "Definitions",
      "excerpt": "‘deep fake’ means AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful",
      "annex": null,
      "point": null,
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Article 5",
      "title": "Prohibited AI practices",
      "excerpt": "The following AI practices shall be prohibited...",
      "annex": null,
      "point": null,
      "citation_role": "exclusion_checked"
    },
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used for the recruitment or selection of natural persons...",
      "annex": "III",
      "point": "4(a)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: Not prohibited under Article 5 since it is not used for social scoring, real-time biometric surveillance, subliminal manipulation causing harm, or vulnerability exploitation. Step 2 analysis: Not high-risk as it does not fall under any categories in Annex III (such as critical infrastructure, education, employment, credit scoring, law enforcement, migration, or justice). Step 3 analysis: The AI system generates synthetic media (deepfakes) depicting people for marketing campaigns, which falls squarely under LIMITED_RISK as an AI-generated media / deepfake system requiring transparency obligations under the EU AI Act.

### Case 12: Student admissions decision support

Expected: Annex III 3(a). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels",
      "annex": "III",
      "point": "3(a)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Article 6",
      "title": "Classification rules for high-risk AI systems",
      "excerpt": "Classification rules and exceptions for high-risk AI systems",
      "annex": null,
      "point": null,
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: The system does not engage in any prohibited practices such as social scoring, real-time biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups under Article 5. Step 2 analysis: The system is designed to evaluate student applications and recommend whether applicants should be admitted to an educational institution. Under Annex III, point 3(a), AI systems intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels are classified as high-risk. Therefore, the system falls under HIGH_RISK.

### Case 13: Internal PDF document type classifier

Expected: none. Failure: genuinely different or missing provision. No returned own identity matches the expected provision, or supporting citations were returned where none was expected.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Article 6",
      "title": "Classification rules for high-risk AI systems",
      "excerpt": "Classification rules for high-risk AI systems",
      "annex": null,
      "point": null,
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to evaluate and classify emergency calls by natural persons...",
      "annex": "III",
      "point": "5(d)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: Not prohibited under Article 5. Step 2 analysis: Does not match any high-risk use cases in Annex III (such as emergency calls under point 5(d)). Step 3 analysis: Not a chatbot, emotion recognition system, AI-generated media, or interactive recommendation system. Step 4 analysis: As an internal PDF document type classifier routing administrative files like invoices and forms, it defaults to MINIMAL_RISK.

### Case 14: Employee promotion monitoring

Expected: Annex III 4(b). Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [
    {
      "article": "Annex III",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to make decisions affecting terms of work-related relationships, the promotion or termination of work-related contractual relationships, to allocate tasks based on individual behaviour or personal traits or characteristics or to monitor and evaluate the performance and behaviour of persons in such relationships.",
      "annex": "III",
      "point": "4(b)",
      "citation_role": "supporting"
    }
  ],
  "exclusions_checked": []
}
```

Model reasoning:

> Step 1 analysis: Not prohibited because the system does not involve social scoring, biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: HIGH_RISK classification applies because the AI system is intended to be used to monitor and evaluate the performance and behaviour of persons in work-related relationships and assist in employee promotion decisions, which matches Annex III, point 4(b).

### Case 15: Internal portfolio capital model

Expected: Annex III 5(b) scope. Failure: formatting mismatch. The canonical own identity matches, but the raw article string does not exactly equal the owner label.

Structured citations returned (including role and split identity fields):

```json
{
  "supporting": [],
  "exclusions_checked": [
    {
      "article": "Annex III, point 5(b)",
      "title": "High-risk AI systems referred to in Article 6(2)",
      "excerpt": "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score, with the exception of AI systems used for the purpose of detecting financial fraud;",
      "annex": "III",
      "point": "5(b)",
      "citation_role": "exclusion_checked"
    }
  ]
}
```

Model reasoning:

> Step 1 analysis: Not prohibited under Article 5 as it does not involve social scoring, real-time biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: Not high-risk under Annex III because the system is used solely to estimate aggregate capital requirements for an internal financial portfolio using portfolio-level exposures and scenarios, making no decisions about individual customers or applicants, thereby avoiding creditworthiness evaluation of natural persons under Annex III, point 5(b). Step 3 analysis: Does not fit limited risk criteria such as conversational systems, emotion recognition, or generative media. Step 4 analysis: Defaulting to MINIMAL_RISK.

# Original runner measurement (preserved)
# Fixed labelled evaluation

Run status: complete. Completed 15/15 cases.
Clear-case accuracy: 13/13; 13 clear cases evaluated.
Unevaluated cases are UNVERIFIED and are not counted as incorrect predictions.
Provision identity matches: 10/15.
Needs review: 0 cases; IDs [].
Provision matching includes checked exclusions. Article paragraph/subparagraph labels must match explicitly; prose mentions do not count. Scope/exception qualifiers require reading the reasoning and are not separately validated.
Grounding checks provision identity, not whether the interpretation or quoted excerpt is correct. Empty citation sets pass the identity check vacuously.

| ID | Name | Difficulty | Expected tier | Predicted tier | Expected provision | Supporting citations | Exclusions checked | Provision match | Grounded | Needs review / reasons | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Retail loan default predictor | clear | HIGH_RISK | HIGH_RISK | Annex III 5(b) | Annex III 5(b) | Annex III 1(b), Annex III 3(b), Annex III 4(a) | True | True | False / none | 0.98 |
| 2 | CV screening and applicant ranking | clear | HIGH_RISK | HIGH_RISK | Annex III 4(a) | Annex III 4(a) | none | True | True | False / none | 0.98 |
| 3 | Email spam filter | clear | MINIMAL_RISK | MINIMAL_RISK | none | none | Article 5, Article 5, Annex III 6(d) | True | True | False / none | 0.95 |
| 4 | Banking FAQ chatbot | clear | LIMITED_RISK | LIMITED_RISK | Article 50(1) | Article 6 | Annex III 5(b) | False | True | False / none | 0.95 |
| 5 | Public authority social scoring | clear | PROHIBITED | PROHIBITED | Article 5(1)(c) | Article 5 | Annex III 5(a) | False | True | False / none | 0.99 |
| 6 | Card transaction fraud detector | ambiguous | MINIMAL_RISK | MINIMAL_RISK | Annex III 5(b) fraud exception | Annex III 5(b) | Article 5 | True | True | False / none | 0.95 |
| 7 | Life and health insurance pricing | clear | HIGH_RISK | HIGH_RISK | Annex III 5(c) | Annex III 5(c) | Annex III 1(b) | True | True | False / none | 0.99 |
| 8 | Exam cheating detection | clear | HIGH_RISK | HIGH_RISK | Annex III 3(d) | Annex III 3(d) | none | True | True | False / none | 0.98 |
| 9 | Workplace employee emotion recognition | clear | PROHIBITED | PROHIBITED | Article 5(1)(f) | Article 5(f) | Annex III 1(c) | False | True | False / none | 0.99 |
| 10 | Marketing deepfake image generator | clear | LIMITED_RISK | LIMITED_RISK | Article 50(4) | Article 3 | Article 5, Annex III 4(a) | False | True | False / none | 0.9 |
| 11 | E-commerce product recommender | clear | MINIMAL_RISK | MINIMAL_RISK | none | none | Annex III 4(a) | True | True | False / none | 0.9 |
| 12 | Student admissions decision support | clear | HIGH_RISK | HIGH_RISK | Annex III 3(a) | Annex III 3(a) | Article 6 | True | True | False / none | 0.98 |
| 13 | Internal PDF document type classifier | clear | MINIMAL_RISK | MINIMAL_RISK | none | Article 6 | Annex III 5(d) | False | True | False / none | 0.9 |
| 14 | Employee promotion monitoring | clear | HIGH_RISK | HIGH_RISK | Annex III 4(b) | Annex III 4(b) | none | True | True | False / none | 0.95 |
| 15 | Internal portfolio capital model | ambiguous | MINIMAL_RISK | MINIMAL_RISK | Annex III 5(b) scope | none | Annex III 5(b) | True | True | False / none | 0.95 |

## Confusion matrix (13 clear cases, expected rows / predicted columns)

| Expected | PROHIBITED | HIGH_RISK | LIMITED_RISK | MINIMAL_RISK | UNCLASSIFIED |
|---|---|---|---|---|---|
| PROHIBITED | 2 | 0 | 0 | 0 | 0 |
| HIGH_RISK | 0 | 6 | 0 | 0 | 0 |
| LIMITED_RISK | 0 | 0 | 2 | 0 | 0 |
| MINIMAL_RISK | 0 | 0 | 0 | 3 | 0 |

## Ambiguous cases and incorrect predictions

### 6: Card transaction fraud detector

Expected MINIMAL_RISK; predicted MINIMAL_RISK; confidence 0.95.

Step 1 analysis: The system does not engage in prohibited practices such as social scoring, biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups under Article 5. Step 2 analysis: While the system operates in the financial sector, Annex III Point 5(b) explicitly excludes AI systems used for the purpose of detecting financial fraud from being classified as high-risk credit scoring or creditworthiness evaluation systems. Step 3 analysis: The system is not a conversational chatbot, emotion recognition system, general-purpose AI-generated media tool, or a recommendation system requiring specific transparency obligations under the limited risk tiers. Step 4 analysis: Since it does not meet the criteria for prohibited, high-risk, or limited-risk tiers, the system defaults to MINIMAL_RISK.

### 15: Internal portfolio capital model

Expected MINIMAL_RISK; predicted MINIMAL_RISK; confidence 0.95.

Step 1 analysis: Not prohibited under Article 5 as it does not involve social scoring, real-time biometric mass surveillance, subliminal manipulation, or exploitation of vulnerable groups. Step 2 analysis: Not high-risk under Annex III because the system is used solely to estimate aggregate capital requirements for an internal financial portfolio using portfolio-level exposures and scenarios, making no decisions about individual customers or applicants, thereby avoiding creditworthiness evaluation of natural persons under Annex III, point 5(b). Step 3 analysis: Does not fit limited risk criteria such as conversational systems, emotion recognition, or generative media. Step 4 analysis: Defaulting to MINIMAL_RISK.

## Usage and cleanup

{
  "live_calls": 30,
  "input_tokens": 70216,
  "output_tokens": 9400,
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
  ],
  "live_calls_upper_bound_including_interruption": 31
}

DELETE endpoint results: [{"system_id": "eval_627e230a_01_ret-a2438a", "status": 204}, {"system_id": "eval_627e230a_02_cv_-02f0aa", "status": 204}, {"system_id": "eval_627e230a_03_ema-13ad78", "status": 204}, {"system_id": "eval_627e230a_04_ban-63a3c0", "status": 204}, {"system_id": "eval_627e230a_05_pub-72b04f", "status": 204}, {"system_id": "eval_627e230a_06_car-210d2a", "status": 204}, {"system_id": "eval_627e230a_07_lif-dad41c", "status": 204}, {"system_id": "eval_627e230a_08_exa-2af131", "status": 204}, {"system_id": "eval_627e230a_09_wor-c53903", "status": 204}, {"system_id": "eval_627e230a_10_mar-a1d831", "status": 204}, {"system_id": "eval_627e230a_11_e_c-ba9ded", "status": 204}, {"system_id": "eval_627e230a_12_stu-fbdf75", "status": 204}, {"system_id": "eval_627e230a_13_int-632428", "status": 204}, {"system_id": "eval_627e230a_14_emp-288cd2", "status": 204}, {"system_id": "eval_627e230a_15_int-ec9d85", "status": 204}]

Stop reason: none

## Frozen input hashes

{
  "tests/fixtures/labelled_set.json": "ad2f88faa995d37bdf73a372f8b7c3b7354318dc1638fc5450491f80361775ac",
  "argus/config.py": "fc4259082c20e3843b9140a9ff2c48f5e9049159ea44b4756d51f02b1f347255",
  "argus/core/agents/registrar.py": "30a88717f68eb0ead7f39bd14c927180e28fb7c3760838ab5d4e5af986e15043",
  "argus/core/agents/risk_classifier.py": "ec1b90b013957bff5a389771d9e87f0dffe7a6b35fb5a91e6a2ad0cfe8561485",
  "argus/core/llm.py": "422ec3baffcb0d949e235a1ada598e619de2542313a83574caef492f76a2ae4e",
  "argus/core/llm_schemas.py": "2e8a4bc715e68ae3c12f186daf0030e4314729ab02554a3f5f6299bf874ac0f7",
  "argus/rag/retriever.py": "f4121e3f2882e872c1d26eb1a30b56e1ac173783de1a09b3d77b79cb248ad985",
  "argus/core/agents/drift_monitor.py": "458756e7ed8cebc8ed7ae74f15541602f0981ce78fa07e30d23aa7f9cbd270cd"
}

## Final verification

- Rebuilt the backend image once at the end; CPU-only torch dependency layers were reused. Build completed in under a minute.
- Plain `pytest -q` in the rebuilt backend image: 60 passed, four deprecation warnings. API keys were disabled for tests.
- All 15 DELETE requests returned 204. Database check: zero active evaluation systems and 15 inactive evaluation systems for this run.
- Docker Compose was brought down without deleting volumes.
- The four generated report/fixture artifacts passed a private exact-key scan; no key was printed or written.
- UNVERIFIED: whether the interruption consumed one additional unlogged call, and its token usage. Thirty calls are logged; the conservative upper bound is 31 of the allowed 34.
- No output-layer citation normalization or post-measurement prompt, retrieval, threshold, label, or recorded-result changes were applied.
