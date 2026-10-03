# EU AI Act RAG diagnosis and evaluation

Both evaluations use the same six queries, cosine-distance search, k=5, and no section filter. No Claude or API key was used.

## Diagnosis before implementation

- 277 chunks; character lengths min/average/max: 18 / 2200.3 / 6959.
- Original primary splitter: independent pages and loose article/section boundary regexes, no size cap, no overlap, no cross-page state. Its fallback (800 characters, 100 overlap) was not used.
- all-MiniLM-L6-v2 max_seq_length: 256 tokens including special tokens. 177 chunks exceeded it.
- 144 chunks were tagged General, not all 277. Loose Article regexes also matched references inside prose.
- Annex III page 126 (printed page 127): 780 tokens; embedded prefix ends at character 983; creditworthiness starts at character 2966. Point 5(b) was outside the embedded prefix.

## Extraction comparison

First 300 characters, zero-based PDF page indexes. PyMuPDF 1.28.2 was initially installed only in the comparison container.

### Page 0 - pypdf

```text
REGUL ATION (EU) 2024/1689 OF THE EUR OPEAN PARLIAMENT AND OF THE COUNCIL
of 13 June 2024
laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, 
(EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and 
Directiv es 2014/90/
```

### Page 0 - pymupdf

```text
REGULATION (EU) 2024/1689 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL
of 13 June 2024
laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, 
(EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and 
Directives 2014/90/EU,
```

### Page 1 - pypdf

```text
guarante eing the unif orm protect ion of overriding reasons of public interest and of rights of persons throughout the 
internal marke t on the basis of Article 114 of the Treaty on the Functioning of the European Union (TFEU). To the 
exte nt that this Regulation contains specif ic rules on the pr
```

### Page 1 - pymupdf

```text
guaranteeing the uniform protection of overriding reasons of public interest and of rights of persons throughout the 
internal market on the basis of Article 114 of the Treaty on the Functioning of the European Union (TFEU). To the 
extent that this Regulation contains specific rules on the protecti
```

### Page 2 - pypdf

```text
(9) Harmonised rules applicable to the placing on the mark et, the putting into service and the use of high-r isk AI 
syste ms should be laid down consistently with Regulation (EC) No 765/2008 of the European Parliament and of the 
Council (7), Decision No 768/2008/EC of the European Parliament and 
```

### Page 2 - pymupdf

```text
(9)
Harmonised rules applicable to the placing on the market, the putting into service and the use of high-risk AI 
systems should be laid down consistently with Regulation (EC) No 765/2008 of the European Parliament and of the 
Council (7), Decision No 768/2008/EC of the European Parliament and of 
```

### Page 126 - pypdf

```text
ANNEX III
High-r isk AI systems referred to in Article 6(2)
High-r isk AI systems pursuant to Article 6(2) are the AI systems listed in any of the follo wing areas:
1. Biometr ics, in so far as their use is permitted under relevant Union or national law:
(a)remote biometr ic identifica tion syste ms
```

### Page 126 - pymupdf

```text
ANNEX III
High-risk AI systems referred to in Article 6(2)
High-risk AI systems pursuant to Article 6(2) are the AI systems listed in any of the following areas:
1.
Biometrics, in so far as their use is permitted under relevant Union or national law:
(a) remote biometric identification systems.
This
```

## Implementation and validation

- PyMuPDF 1.28.2 selected for cleaner extraction. Its binary wheel imported and extracted the document without additional system-library installation in the backend container.
- Exact standalone Article/ANNEX headings, bold font hints for wrapped titles, and cross-page provision state. Before Chapter I the text is tagged recital. Running page headers/footers are removed.
- Metadata includes section_type, article_number/article_title, annex_id/annex_title, Annex III point/subpoint, citation, source, and zero-based/one-based page spans.
- Each sub-chunk repeats its provision heading. The token limit includes that heading and special tokens. Body overlap targets 24 tokens; whole-word boundaries can increase it slightly. Annex III is split by numbered areas and lettered subpoints.
- 574 chunks: 200 recital, 297 article, 77 annex. All 113 articles and all 13 annexes validated.
- Character lengths min/average/max: 107 / 1136.6 / 1611. Tokens min/average/max: 28 / 220.6 / 256. No chunk exceeds 256 tokens.
- Ingestion replaced the framework collection: 574 stored rows, 384-dimensional vectors.

### Annex III 5(b) sample

```text
Annex III, point 5(b) - High-risk AI systems referred to in Article 6(2)
(b) AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score, with the exception of AI systems used for the purpose of detecting financial fraud;
```

```json
{
  "source": "eu_ai_act.pdf",
  "framework": "EU_AI_ACT",
  "section_type": "annex",
  "article": "Annex III",
  "article_number": null,
  "article_title": null,
  "annex_id": "III",
  "annex_title": "High-risk AI systems referred to in Article 6(2)",
  "annex_point": "5",
  "annex_subpoint": "b",
  "title": "High-risk AI systems referred to in Article 6(2)",
  "heading_page": 126,
  "citation": "Annex III, point 5(b)",
  "page": 126,
  "page_end": 126,
  "page_number": 127,
  "page_number_end": 127,
  "chunk_index": 0
}
```

## Before/after evaluation

PASS means the expected provision is identifiable in the top five. Legacy chunks are checked by a standalone heading in their full text (plus point 5 and credit-scoring text for Annex III). New chunks use authoritative section/article/annex metadata. An unlabeled legacy continuation cannot establish a reliable citation. Passing references to another provision do not count as that provision.

| Query | Expected | Before | Before rank | After | After rank |
|---|---|---|---|---|---|
| credit scoring | Annex III point 5 | PASS | 5 | PASS | 1 |
| high-risk classification | Article 6 | FAIL | - | PASS | 2 |
| data and bias | Article 10 | PASS | 2 | PASS | 2 |
| human oversight | Article 14 | PASS | 1 | PASS | 1 |
| logging | Article 12 | PASS | 1 | PASS | 1 |
| accuracy and robustness | Article 15 | FAIL | - | PASS | 1 |

## Before: all top-five results

### credit scoring

Query: AI system used to evaluate creditworthiness of natural persons

Expected: Annex III point 5; PASS; rank: 5.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.531229 | legacy/unknown | General | - | 11 | adop ted on the basis of Article 16 TFEU, or subject to their application, which relate to the processing of personal  d |
| 2 | 0.552991 | legacy/unknown | General | - | 16 | to be used for risk assessment and pricing in relation to natural persons for health and life insurance can also have  a |
| 3 | 0.562205 | legacy/unknown | Article 82 | - | 107 | Article 82 Compliant AI systems which present a risk 1. Where, having perfor med an evaluation under Article 79, after c |
| 4 | 0.582717 | legacy/unknown | Article 50 | - | 81 | Article 50 Transparency obligations for providers and deplo yers of certain AI systems 1. Providers shall ensure that AI |
| 5 | 0.589183 | legacy/unknown | General | - | 126 | ANNEX III High-r isk AI systems referred to in Article 6(2) High-r isk AI systems pursuant to Article 6(2) are the AI sy |

### high-risk classification

Query: What rules determine whether an AI system is classified as high-risk?

Expected: Article 6; FAIL; rank: -.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.358392 | legacy/unknown | Article 8 | - | 54 | Article 8 Compliance with the requirements 1. High-r isk AI systems shall comp ly with the requirements laid down in thi |
| 2 | 0.413026 | legacy/unknown | Article 82 | - | 107 | Article 82 Compliant AI systems which present a risk 1. Where, having perfor med an evaluation under Article 79, after c |
| 3 | 0.450170 | legacy/unknown | General | - | 20 | (72) To address concer ns relate d to opacity and complexity of certain AI systems and help deplo yers to fulfil their   |
| 4 | 0.453888 | legacy/unknown | General | - | 53 | 3. By derogat ion from paragraph 2, an AI system referred to in Annex III shall not be considered to be high-r isk where |
| 5 | 0.469148 | legacy/unknown | General | - | 7 | (27) While the risk-based approac h is the basis for a propor tionate and effective set of binding rules, it is imp orta |

### data and bias

Query: What are the requirements for training data quality and detecting and correcting bias in high-risk AI systems?

Expected: Article 10; PASS; rank: 2.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.485255 | legacy/unknown | Article 8 | - | 54 | Article 8 Compliance with the requirements 1. High-r isk AI systems shall comp ly with the requirements laid down in thi |
| 2 | 0.504933 | legacy/unknown | Article 10 | - | 56 | Article 10 Data and data governance 1. High-r isk AI syste ms which mak e use of techniques involving the training of AI |
| 3 | 0.520955 | legacy/unknown | General | - | 19 | (feedbac k loops). Biases can for example be inherent in underlying data sets, especially when histor ical data is being |
| 4 | 0.536410 | legacy/unknown | General | - | 47 | (27) ‘harmonised standard’ means a harmonised standard as defined in Article 2(1), point (c), of Regulation (EU)  No 102 |
| 5 | 0.558442 | legacy/unknown | General | - | 7 | (27) While the risk-based approac h is the basis for a propor tionate and effective set of binding rules, it is imp orta |

### human oversight

Query: What human oversight measures are required for high-risk AI systems?

Expected: Article 14; PASS; rank: 1.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.356664 | legacy/unknown | Article 14 | - | 59 | Article 14 Human oversight 1. High-r isk AI systems shall be designed and developed in such a way, including with approp |
| 2 | 0.409628 | legacy/unknown | Article 13; | - | 68 | Article 13; (e)a descr iption of the imp lementation of human oversight measures, according to the instr uctions for use |
| 3 | 0.414018 | legacy/unknown | Article 8 | - | 54 | Article 8 Compliance with the requirements 1. High-r isk AI systems shall comp ly with the requirements laid down in thi |
| 4 | 0.420108 | legacy/unknown | General | - | 7 | (27) While the risk-based approac h is the basis for a propor tionate and effective set of binding rules, it is imp orta |
| 5 | 0.439558 | legacy/unknown | Article 82 | - | 107 | Article 82 Compliant AI systems which present a risk 1. Where, having perfor med an evaluation under Article 79, after c |

### logging

Query: What automatic logging and record-keeping capabilities must high-risk AI systems provide?

Expected: Article 12; PASS; rank: 1.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.417244 | legacy/unknown | General | - | 58 | Article 12 Record-ke eping 1. High-r isk AI syste ms shall technically allow for the auto matic recording of events (log |
| 2 | 0.457147 | legacy/unknown | Article 19 | - | 63 | Article 19 Aut omatically generated logs 1. Providers of high-r isk AI syste ms shall keep the logs refer red to in Arti |
| 3 | 0.463597 | legacy/unknown | Article 8 | - | 54 | Article 8 Compliance with the requirements 1. High-r isk AI systems shall comp ly with the requirements laid down in thi |
| 4 | 0.468712 | legacy/unknown | General | - | 33 | (133) A variety of AI systems can generate large quantities of synthetic cont ent that becomes increasing ly hard for hu |
| 5 | 0.490661 | legacy/unknown | General | - | 38 | (154) The national compet ent author ities should exercise their powers independently , imp artially and without bias, s |

### accuracy and robustness

Query: What accuracy, robustness and cybersecurity requirements apply to high-risk AI systems?

Expected: Article 15; FAIL; rank: -.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.356231 | legacy/unknown | Article 8 | - | 54 | Article 8 Compliance with the requirements 1. High-r isk AI systems shall comp ly with the requirements laid down in thi |
| 2 | 0.470401 | legacy/unknown | General | - | 20 | (72) To address concer ns relate d to opacity and complexity of certain AI systems and help deplo yers to fulfil their   |
| 3 | 0.470558 | legacy/unknown | General | - | 21 | (75) Technical robustness is a key requirement for high-r isk AI systems. They should be resilient in relation to harmfu |
| 4 | 0.473918 | legacy/unknown | Article 82 | - | 107 | Article 82 Compliant AI systems which present a risk 1. Where, having perfor med an evaluation under Article 79, after c |
| 5 | 0.479181 | legacy/unknown | General | - | 7 | (27) While the risk-based approac h is the basis for a propor tionate and effective set of binding rules, it is imp orta |

## After: all top-five results

### credit scoring

Query: AI system used to evaluate creditworthiness of natural persons

Expected: Annex III point 5; PASS; rank: 1.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.293838 | annex | - | III / 5(b) | 126 | Annex III, point 5(b) - High-risk AI systems referred to in Article 6(2) (b) AI systems intended to be used to evaluate  |
| 2 | 0.344247 | recital | - | - | 15 | Recitals high risk to legal and natural persons. In addition, AI systems used to evaluate the credit score or creditwort |
| 3 | 0.369737 | recital | - | - | 15 | Recitals necessary for people to fully participate in society or to improve one’s standard of living. In particular, nat |
| 4 | 0.473569 | annex | - | III / 5(c) | 126 | Annex III, point 5(c) - High-risk AI systems referred to in Article 6(2) (c) AI systems intended to be used for risk ass |
| 5 | 0.492562 | recital | - | - | 8 | Recitals non-discrimination and the values of equality and justice. Such AI systems evaluate or classify natural persons |

### high-risk classification

Query: What rules determine whether an AI system is classified as high-risk?

Expected: Article 6; PASS; rank: 2.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.295384 | recital | - | - | 13 | Recitals those that are safety components of products, or that are themselves products, it is appropriate to classify th |
| 2 | 0.296418 | article | 6 | - | 52 | Article 6 - Classification rules for high-risk AI systems 1. Irrespective of whether an AI system is placed on the marke |
| 3 | 0.314035 | recital | - | - | 13 | Recitals is appropriate to classify them as high-risk under this Regulation if the product concerned undergoes the confo |
| 4 | 0.315401 | article | 6 | - | 53 | Article 6 - Classification rules for high-risk AI systems considered to be high-risk where it does not pose a significan |
| 5 | 0.318752 | article | 14 | - | 59 | Article 14 - Human oversight 1. High-risk AI systems shall be designed and developed in such a way, including with appro |

### data and bias

Query: What are the requirements for training data quality and detecting and correcting bias in high-risk AI systems?

Expected: Article 10; PASS; rank: 2.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.255426 | recital | - | - | 18 | Recitals for the high-risk AI system by the provider to address foreseeable misuse. The providers however are encouraged |
| 2 | 0.366234 | article | 10 | - | 56 | Article 10 - Data and data governance 1. High-risk AI systems which make use of techniques involving the training of AI  |
| 3 | 0.369932 | article | 10 | - | 56 | Article 10 - Data and data governance persons, have a negative impact on fundamental rights or lead to discrimination pr |
| 4 | 0.398151 | recital | - | - | 18 | Recitals data governance and management practices. Data sets for training, validation and testing, including the labels, |
| 5 | 0.405865 | annex | - | III / 3 | 126 | Annex III, point 3 - High-risk AI systems referred to in Article 6(2) 3. Education and vocational training: |

### human oversight

Query: What human oversight measures are required for high-risk AI systems?

Expected: Article 14; PASS; rank: 1.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.157852 | article | 14 | - | 59 | Article 14 - Human oversight 1. High-risk AI systems shall be designed and developed in such a way, including with appro |
| 2 | 0.236002 | article | 14 | - | 59 | Article 14 - Human oversight deployer. 4. For the purpose of implementing paragraphs 1, 2 and 3, the high-risk AI system |
| 3 | 0.323029 | recital | - | - | 7 | Recitals (27) While the risk-based approach is the basis for a proportionate and effective set of binding rules, it is i |
| 4 | 0.326165 | recital | - | - | 18 | Recitals adopt the most appropriate risk-management measures in light of the state of the art in AI. When identifying th |
| 5 | 0.326492 | article | 26 | - | 66 | Article 26 - Obligations of deployers of high-risk AI systems 1. Deployers of high-risk AI systems shall take appropriat |

### logging

Query: What automatic logging and record-keeping capabilities must high-risk AI systems provide?

Expected: Article 12; PASS; rank: 1.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.178191 | article | 12 | - | 58 | Article 12 - Record-keeping 1. High-risk AI systems shall technically allow for the automatic recording of events (logs) |
| 2 | 0.266031 | recital | - | - | 19 | Recitals 9(2), point (g) of Regulation (EU) 2016/679 and Article 10(2), point (g) of Regulation (EU) 2018/1725. (71) Hav |
| 3 | 0.273534 | article | 19 | - | 63 | Article 19 - Automatically generated logs 1. Providers of high-risk AI systems shall keep the logs referred to in Articl |
| 4 | 0.352603 | article | 21 | - | 63 | Article 21 - Cooperation with competent authorities 1. Providers of high-risk AI systems shall, upon a reasoned request  |
| 5 | 0.361189 | article | 26 | - | 67 | Article 26 - Obligations of deployers of high-risk AI systems shall keep the logs automatically generated by that high-r |

### accuracy and robustness

Query: What accuracy, robustness and cybersecurity requirements apply to high-risk AI systems?

Expected: Article 15; PASS; rank: 1.

| Rank | Distance | section_type | Article | Annex / point | PDF page | First 120 characters |
|---|---|---|---|---|---|---|
| 1 | 0.201626 | article | 15 | - | 60 | Article 15 - Accuracy, robustness and cybersecurity 1. High-risk AI systems shall be designed and developed in such a wa |
| 2 | 0.274495 | article | 15 | - | 60 | Article 15 - Accuracy, robustness and cybersecurity achieved through technical redundancy solutions, which may include b |
| 3 | 0.290847 | recital | - | - | 21 | Recitals ensuring that AI systems are resilient against attempts to alter their use, behaviour, performance or compromis |
| 4 | 0.306215 | recital | - | - | 20 | Recitals available on the market of measuring instruments (OJ L 96, 29.3.2014, p. 149). (75) Technical robustness is a k |
| 5 | 0.313215 | article | 13 | - | 58 | Article 13 - Transparency and provision of information to deployers and validated and which can be expected, and any kno |

## Remaining retrieval limitation

Recitals remain in 12 of the 30 top-five slots and rank first for classification and data/bias. Credit scoring has 3 recitals in its top five. A proposed optional PGVector metadata filter would restrict provision lookup to section_type in [article, annex]. The user elected to keep retrieval unfiltered this round. No filter was applied to either evaluation.

Article 6 is retrieved at rank 2 by the classification query. It does not appear in the credit-scoring top five; Annex III 5(b), which references Article 6(2), is rank 1.

## Pytest regression

Default pytest initially returned 3 passed and 1 fixture-source error. At fixture setup, event_loop.__code__.co_filename pointed at the Windows host path C:\Users\Akshatha\OneDrive\Desktop\ARGUS\argus\tests\conftest.py; that path does not exist in the Linux container. Docker had copied host pytest assertion-rewrite bytecode.

Clearing only /app/tests/__pycache__ made unchanged default pytest -q pass all 4 tests. .dockerignore now excludes __pycache__, *.pyc, and .pytest_cache to prevent recurrence. No fixture changes and no --assert=plain workaround were used.

## Final image verification

The single final backend rebuild succeeded below the 15-minute cutoff. A fresh container from that image passed default pytest -q (4 passed) and the same retrieval evaluation (6/6 PASS, identical ranks). It extracted all 144 pages with PyMuPDF 1.28.2. Torch was 2.14.1+cpu, CUDA was absent, and no CUDA/NVIDIA distributions were installed. Psycopg 3.2.1 used its binary implementation. The fresh image contained neither .env nor copied test bytecode caches before pytest ran. The API key was explicitly empty.

UNVERIFIED: semantic retrieval quality beyond these six queries and ingestion of other regulatory PDFs/frameworks.
