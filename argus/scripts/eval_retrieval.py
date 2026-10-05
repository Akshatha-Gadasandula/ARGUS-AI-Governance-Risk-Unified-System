"""Evaluate fixed EU AI Act queries against the unfiltered top five results.

Run from the project root: python -m scripts.eval_retrieval --output results.json
Legacy chunks are checked by full heading text because their citation metadata
is incomplete. New chunks are checked by their structured citation metadata.
"""
import argparse
import json
import os
import re
from pathlib import Path

from argus.rag.retriever import RegulatoryRetriever


CASES = [
    ("credit scoring", "AI system used to evaluate creditworthiness of natural persons", "annex", "III", "5"),
    ("high-risk classification", "What rules determine whether an AI system is classified as high-risk?", "article", "6", None),
    ("data and bias", "What are the requirements for training data quality and detecting and correcting bias in high-risk AI systems?", "article", "10", None),
    ("human oversight", "What human oversight measures are required for high-risk AI systems?", "article", "14", None),
    ("logging", "What automatic logging and record-keeping capabilities must high-risk AI systems provide?", "article", "12", None),
    ("accuracy and robustness", "What accuracy, robustness and cybersecurity requirements apply to high-risk AI systems?", "article", "15", None),
]


def matches(doc, section_type, number, point):
    """Match the provision itself, not a passing reference to another article."""
    metadata = doc.metadata
    if "section_type" in metadata:
        if metadata["section_type"] != section_type:
            return False
        if section_type == "article":
            return str(metadata.get("article_number")) == number
        return metadata.get("annex_id") == number and str(metadata.get("annex_point")) == point
    if section_type == "article":
        return bool(re.search(rf"^Article\s+{number}\s*$", doc.page_content, re.M | re.I))
    return bool(
        re.search(rf"^ANNEX\s+{number}\s*$", doc.page_content, re.M | re.I)
        and re.search(rf"^{point}\.\s*", doc.page_content, re.M)
        and re.search(r"credit\s*wo\s*rthiness|credit\s*score", doc.page_content, re.I)
    )


def evaluate(db_url, classification=False):
    retriever = RegulatoryRetriever(db_url)
    if not retriever.retrieve("EU_AI_ACT", CASES[0][1], k=5):
        raise RuntimeError("EU AI Act retrieval returned no documents")
    store = retriever.stores["regulations_eu_ai_act"]
    report = []
    for name, query, section_type, number, point in CASES:
        results = retriever.retrieve_for_classification_with_score("EU_AI_ACT", query, k=5) if classification else store.similarity_search_with_score(query, k=5)
        context_chunks=len(results)
        results=results[:5]  # Preserve the original top-five evaluation after context expansion.
        expected = f"Article {number}" if section_type == "article" else f"Annex {number} point {point}"
        hits = []
        for rank, (doc, distance) in enumerate(results, 1):
            hit = {
                "rank": rank,
                "distance": float(distance),
                "section_type": doc.metadata.get("section_type", "legacy/unknown"),
                "article": doc.metadata.get("article_number", doc.metadata.get("article")),
                "annex": doc.metadata.get("annex_id"),
                "annex_point": doc.metadata.get("annex_point"),
                "metadata": doc.metadata,
                "first_120_chars": doc.page_content[:120],
                "expected_match": matches(doc, section_type, number, point),
            }
            hits.append(hit)
        hit_rank = next((hit["rank"] for hit in hits if hit["expected_match"]), None)
        case = {"name": name, "query": query, "expected": expected, "result": "PASS" if hit_rank else "FAIL", "hit_rank": hit_rank, "context_chunks":context_chunks,"top_5": hits}
        report.append(case)
        print(f"\n{name}: {query}\nExpected: {expected}", flush=True)
        for hit in hits:
            print(f"  {hit['rank']}. distance={hit['distance']:.6f} section_type={hit['section_type']} article={hit['article']} annex={hit['annex']} point={hit['annex_point']} text={hit['first_120_chars']!r}", flush=True)
        print(f"{case['result']} (rank={hit_rank})", flush=True)
    print("\n| Query | Expected | Result | Rank |\n|---|---|---|---|", flush=True)
    for case in report:
        print(f"| {case['name']} | {case['expected']} | {case['result']} | {case['hit_rank'] or '-'} |", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--output", type=Path, help="Optional JSON report with all top-five results")
    parser.add_argument("--classification", action="store_true", help="Evaluate filtered classification retrieval with pinned provisions")
    args = parser.parse_args()
    if not args.db_url:
        parser.error("Set DATABASE_URL or supply --db-url")
    report = evaluate(args.db_url, args.classification)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
