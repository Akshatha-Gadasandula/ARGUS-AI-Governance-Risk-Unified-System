# Full prohibition screen and supporting-citation checks

No live LLM calls were made. The held-out labels, recorded results and recorded report are byte-identical to their originals, verified with SHA256. Separate offline artifacts do not modify model outputs.

## Retrieval and context size

Every EU classification includes all Article 5 paragraph 1 chunks: indices 0–4 in the indexed corpus. Chunk 4 includes the continuation of point (h) and the paragraph 2 boundary. Selection follows the paragraph boundaries and contiguous chunk order, independent of query relevance and owner labels. Article 6, Article 50, the best Annex III chunk and one additional unique non-recital result remain included. The resulting context is **nine chunks**. Distance scoring and distance ordering are unchanged.

The retrieval query is now exactly the user-submitted purpose; Registrar-inferred model/output types are never appended. A regression test compares retrieved chunk identities for identical purposes with two different Registrar outputs.

Local tokenizer counts for all ten saved descriptions, with no truncation:

| Case | Chunks | All Article 5(1)(a)–(h) present | Passage-context tokens | Full input-payload tokens |
|---|---|---|---|---|
| 1 | 9 | Yes | 2,218 | 7,731 |
| 2 | 9 | Yes | 2,049 | 7,382 |
| 3 | 9 | Yes | 2,194 | 7,671 |
| 4 | 9 | Yes | 2,135 | 7,579 |
| 5 | 9 | Yes | 2,091 | 7,473 |
| 6 | 9 | Yes | 2,037 | 7,385 |
| 7 | 9 | Yes | 1,988 | 7,269 |
| 8 | 9 | Yes | 2,159 | 7,630 |
| 9 | 9 | Yes | 2,045 | 7,398 |
| 10 | 9 | Yes | 2,165 | 7,612 |

Counts use the installed all-MiniLM-L6-v2 WordPiece tokenizer. They are **not Gemini tokenizer counts**. Tokenization is untruncated and is not an embedding inference of the full context. The full payload exceeds 5,000 locally measured tokens because the existing LLM layer includes both formatted passages and a JSON copy of chunks, plus the prompt/schema. This was reported before continuing. The transport was not changed. Inferred prompt fields can change full payload size slightly; measurements use Unspecified fields.

The original top-five retrieval evaluation was preserved even though classification now returns nine chunks:

| Query | Before | After |
|---|---|---|
| Credit scoring | PASS, rank 1 | PASS, rank 1 |
| High-risk classification | PASS, rank 1 | PASS, rank 1 |
| Data and bias | PASS, rank 1 | PASS, rank 1 |
| Human oversight | PASS, rank 1 | PASS, rank 1 |
| Logging | PASS, rank 1 | PASS, rank 1 |
| Accuracy and robustness | PASS, rank 1 | PASS, rank 1 |

Scores: **6/6 before and after**. Full results: [before](prohibition_retrieval_before.json), [after](prohibition_retrieval_after.json). Final token/coverage records: [prohibition_context_tokens_after.json](prohibition_context_tokens_after.json).

## Safety guard

Before calling the classifier LLM, check the paragraph 1 start, paragraph 2 boundary, contiguous Article 5 chunk IDs and the eight clause markers within paragraph 1. Missing coverage returns `status="context_incomplete"`, `risk_tier=null`, `confidence=null`, `needs_review=true` and reason `prohibited_screen_incomplete`, with no citations, obligations or LLM generation. Overall review flags include this status.

The registry's existing non-null enum stores UNCLASSIFIED internally when no tier exists; the detailed classification/API response exposes null tier and context_incomplete status. Tests verify the classifier and API response shape without live requests.

## Exactly what changed in citation output

- Classification supporting citations now use SupportingCitation, which requires the keys `paragraph`, `point` and `incomplete_reason`. Values may be null. These keys are required for all supporting items so the JSON schema is explicit; conditional validation applies to Articles 5/50.
- For supporting Articles 5/50, a null paragraph or point requires a nonblank incomplete_reason. Paragraph must be an explicit numeric string or null. Article 5 point must be a single letter a–h or null.
- Article 50 paragraphs without lettered subpoints use point=null with a not-applicable explanation; an explicit paragraph still makes the canonical identity complete.
- Supporting Article 5 must have both paragraph and lettered point to be complete and satisfy the prohibited-tier consistency check. No omitted paragraph is inferred.
- Canonical strings preserve raw fields. Completeness checks and incomplete flags apply only to supporting citations. Checked exclusions retain their permissive Citation schema and are exempt from these checks; grounding still applies.
- In EU_AI_ACT_PROMPT, after “Think through each classification step carefully. Then respond ONLY with valid JSON:”, a citation-output-format instruction was added, and the sample citation now includes paragraph=null, point="5(b)", incomplete_reason=null.
- In EU_AI_ACT_FALLBACK_PROMPT, after “Analyze this system step-by-step. Respond ONLY with valid JSON:”, the corresponding output-format instruction was added and the sample citation includes the new nullable fields.
- The classification framework and rules before those output sections are unchanged. Both RBI prompt strings are unchanged. AST comparisons against HEAD verified all four preservation checks.

## Offline rescoring

See [offline rescoring, NOT a new measurement; the model outputs are unchanged](offline_heldout_rescoring.md) and [JSON](../tests/fixtures/offline_heldout_rescoring.json).

Needs review changes from 10/10 to **3/10**, cases **3, 7, 9**. Canonical matches remain **6/10**. Case 5 remains incorrectly MINIMAL_RISK and loses its exclusion-only completeness flag. No model output is corrected, no missing paragraph is invented, and the new retrieval guard is not replayed against historical contexts. The effect of the new full screen on model decisions is UNVERIFIED until a future live measurement.

## Verification

Mock-only plain pytest after source copies: **94 passed**, four existing deprecation warnings. Tests cover all-screen pinning, missing-clause/boundary rejection, invariant retrieval across Registrar outputs, exclusion exemption, schema requirements, null reasons, prohibited paragraph/point support, null-tier API responses and read-only rescoring.

UNVERIFIED: exact Gemini token counts, Gemini acceptance/output behavior for the new schema, and live classification accuracy with the expanded context. No live calls were authorized or made.

Final rebuilt-image check: plain pytest -q with API keys disabled passed 94 tests (four deprecation warnings). The one backend rebuild completed in under a minute and reused CPU-only torch/dependency layers. No commit or push was performed.
Compose is down; postgres_data and prometheus_data volumes are present.
