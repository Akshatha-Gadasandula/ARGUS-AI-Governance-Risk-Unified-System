# Classification retrieval and citation output verification

No live Gemini calls were made in this run. Prompts, thresholds, owner labels and previously recorded model results were not changed.

## Original diagnostic contexts

The twenty chunks (section type, article/annex, point/subpoint, first 100 characters) are printed in [classification_context_before.txt](classification_context_before.txt). Queries reconstruct the classifier query using each original purpose and the model/output types from its saved registration response.

| Labelled case | Five chunk identities, in distance order | Article 50 present | Article 5(1) text present |
|---|---|---|---|
| 4: Banking FAQ chatbot | Article 19; Annex IV; Annex VII; Annex III 5(b); Article 6 | No | No |
| 5: Public authority social scoring | Annex III 5(a); Annex III 6(d); Article 5; Article 3; Article 6 | No | Yes: paragraph 1(c), social scoring, and part of (d); paragraph number itself is outside this sub-chunk |
| 10: Marketing deepfake generator | Article 5; Article 3; Article 5; Annex III 4(a); Article 6 | No | Yes: paragraph 1(a)-(c) and (e)-(g) in the two Article 5 sub-chunks |
| 13: Internal PDF classifier | Article 11; Annex VII; Annex VII; Annex III 5(d); Article 6 | No | No |

## Retrieval change

Exactly five EU classification slots: the best-scoring chunk from Article 5, Article 6, Article 50 and Annex III, followed by the top-scoring remaining unique non-recital chunk. Existing embeddings, similarity distances and final distance ordering are unchanged. A remaining chunk may be from another part of an already pinned provision. Missing pinned provisions fail explicitly.

`python -m scripts.eval_retrieval --classification` was run before and after:

| Query | Expected provision | Before | After |
|---|---|---|---|
| Credit scoring | Annex III point 5 | PASS, rank 1 | PASS, rank 1 |
| High-risk classification | Article 6 | PASS, rank 1 | PASS, rank 1 |
| Data and bias | Article 10 | PASS, rank 1 | PASS, rank 1 |
| Human oversight | Article 14 | PASS, rank 1 | PASS, rank 1 |
| Logging | Article 12 | PASS, rank 1 | PASS, rank 1 |
| Accuracy and robustness | Article 15 | PASS, rank 1 | PASS, rank 1 |

Both scores are **6/6**. Full distances and snippets: [before](retrieval_pins_before.json), [after](retrieval_pins_after.json).

All four diagnostic contexts now contain Article 50 and Article 5. See [classification_context_after.txt](classification_context_after.txt). The best Article 5 chunk for cases 4 and 13 is from later biometric-identification safeguards, rather than paragraph 1's prohibition list. Pinning a single chunk does not imply that every paragraph of an article is present. No chunking changes or context expansion were applied.

## Deterministic output layer

`canonical_citation` is added without overwriting the raw `article`, `annex`, `point`, `title`, `excerpt` or `citation_role`. Explicit paragraph/point fields or suffixes are combined. Examples:

```json
{"article":"Annex III","annex":"III","point":"5(b)","canonical_citation":"Annex III point 5(b)","citation_incomplete":false}
{"article":"Article 5","point":"f","canonical_citation":"Article 5(f)","citation_incomplete":true}
{"article":"Article 5(1)(f)","canonical_citation":"Article 5(1)(f)","citation_incomplete":false}
```

Paragraph 1 is never inferred for Article 5. Both paragraph and letter are required for a complete Article 5 citation. Incomplete EU citations add `incomplete_citation` to review reasons. Explicitly excluded citations go in `exclusions_checked`; Article 5 is excluded for minimal/limited tiers and Article 6 for minimal tiers.

Supporting citations drive label-independent consistency flags:

- PROHIBITED without Article 5 containing an explicit paragraph.
- LIMITED_RISK without Article 50.
- HIGH_RISK without Annex III or Article 6(1).
- MINIMAL_RISK with a supporting citation.

The existing grounding check validates article/annex identity and Annex III points; it does not independently validate article paragraph text or the truth of an excerpt. Canonicalization does not strengthen that check.

## Held-out evaluation: UNVERIFIED

`tests/fixtures/heldout_set.json` is absent from the workspace. The owner's file was requested; no substitute labels were created. Estimated registration calls would be twice the number of cases, but the actual estimate cannot be calculated without the set. The runner refuses estimates above 24 when invoked with `--call-cap 24`, requires a backend process budget at most that cap, refuses overwriting prior results, freezes the supplied set and code, and deletes evaluation registrations in cleanup.

The runner now reports strict raw-string matches, canonicalized matches and tier accuracy separately, with per-case review reasons/confidence and an all-case confusion matrix. Canonicalized evaluation does not infer a missing Article 5 paragraph. Expected `none` requires no supporting citations; for non-none labels both supporting citations and checked exclusions are considered, preserving exception/scope cases.

No held-out registrations were created. Held-out scores, per-case results, confusion matrix, live review frequency and deletion results are **UNVERIFIED**.

## Final checks and cleanup

- Plain `pytest -q`, keys disabled, after source copies: 80 passed, four deprecation warnings.
- One backend rebuild completed in under a minute using cached CPU-only torch/dependency layers.
- The final direct-script import-path fix was copied and `python scripts/run_labelled_eval.py --help` passed. That final runner-only fix is not baked into the image; the image supports the module invocation `python -m scripts.run_labelled_eval`. Application code is baked into the rebuilt image.
- No live calls were made; held-out evaluation is blocked by the absent owner-labelled file.
- Prior labelled set/results/report and provider prompts were not modified.
- Rebuilt-image plain pytest: 80 passed, four warnings. Docker Compose is down; postgres_data and prometheus_data volumes are present.
