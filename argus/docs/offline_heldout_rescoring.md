# offline rescoring, NOT a new measurement; the model outputs are unchanged

Supporting completeness and deterministic output flags only; no new retrieval, guard replay, schema repair, inferred clauses or model generation.

Needs review: 10/10 originally; 3/10 offline. Offline cases: [3, 7, 9].
Canonical matches: 6/10 originally; 6/10 offline.

| Case | Original review | Offline review | Offline reasons | Original canonical match | Offline canonical match |
|---|---|---|---|---|---|
| 1 | True | False | none | True | True |
| 2 | True | False | none | True | True |
| 3 | True | True | incomplete_citation | False | False |
| 4 | True | False | none | True | True |
| 5 | True | False | none | False | False |
| 6 | True | False | none | True | True |
| 7 | True | True | incomplete_citation | False | False |
| 8 | True | False | none | True | True |
| 9 | True | True | tier_citation_inconsistent:prohibited_without_article_5_paragraph, incomplete_citation | False | False |
| 10 | True | False | none | True | True |

Case 5 remains incorrectly MINIMAL_RISK and loses its output-completeness flag because only checked exclusions were incomplete. This rescoring does not rerun classification or correct its missing prohibition context. New retrieval/safety behavior needs a future live measurement to establish its effect.

All model response fields, tiers, reasoning and recorded files are unchanged. Old responses are not validated/repaired against the new generation schema; no missing paragraphs or points are invented.