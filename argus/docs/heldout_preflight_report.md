# Held-out preflight: no live calls

Article 5 was already selected by query-dependent `similarity_search_with_score(query, k=1, filter={section_type: article, article_number: 5})`, rather than a fixed document. This behavior is retained and documented; a new regression test proves different synthetic queries select different nearest Article 5 chunks. No labels, thresholds, prompts, embeddings or distance scoring changed.

The remaining slots stay Article 6, Article 50, the best Annex III chunk and one additional unique non-recital chunk, within five total, ordered by unchanged distance.

## Retrieval evaluation

`python -m scripts.eval_retrieval --classification` was run before and after. Both are **6/6**, with each expected provision at rank 1.

| Query | Before | After |
|---|---|---|
| Credit scoring | PASS | PASS |
| High-risk classification | PASS | PASS |
| Data and bias | PASS | PASS |
| Human oversight | PASS | PASS |
| Logging | PASS | PASS |
| Accuracy and robustness | PASS | PASS |

Full results and distances: [before](heldout_retrieval_before.json), [after](heldout_retrieval_after.json).

## Article 5 pins reported before the live run

| Case | Selected Article 5 chunk | PDF pages (one-based) | Distance | Target clause text present |
|---|---|---|---|---|
| 5: Elderly Product Targeting Engine | chunk_index 0 | 51 | 0.738170563 | Yes: paragraph 1(b), exploitation of age-related vulnerabilities |
| 9: Classroom Emotion Monitor | chunk_index 2 | 51–52 | 0.740645214 | Yes: paragraph 1(f), emotion inference in workplaces and educational institutions |

The diagnostic used purpose only, before any Registrar inference, with no hardcoded model or output type. Actual classification adds Registrar-inferred types to the retrieval query, so a later selection may differ. No selection was tuned to these cases. Full selected text/metadata are in [heldout_article5_pins.json](heldout_article5_pins.json).

## Run controls

- Ten EU-only registrations: estimated 20 live calls, hard cap 24.
- Fresh backend process enforcing LLM_MAX_CALLS=24 through a temporary Compose override; .env unchanged.
- GEMINI provider, API key/model presence, cap=24 and positive RPM were checked as booleans only.
- Mock-only plain pytest before live measurement: 82 passed, four existing deprecation warnings.
- Held-out set SHA256: 083d57d2b922bf5075bd3cc48fefbf71eaf41d595ff7fca4f01fdba1700c6a16.
- The runner freezes source/set hashes, never repeats a POST, and keeps terminal provider failures out of accuracy metrics as not completed. Cleanup uses DELETE.
