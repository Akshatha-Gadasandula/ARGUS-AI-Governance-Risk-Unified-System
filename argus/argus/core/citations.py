"""Deterministic citation presentation and tier checks; raw fields are retained."""
import re


def canonicalize_citation(citation, *, supporting=True):
    result = dict(citation)
    label = citation.get('article') or ''
    article = re.search(r'\bArticle\s+(\d+)((?:\([0-9a-z]+\))*)', label, re.I)
    if not article and label.strip().isdigit():
        article = re.match(r'(\d+)()', label.strip())
    incomplete = False
    if article:
        parts = re.findall(r'\(([0-9a-z]+)\)', article[2], re.I)
        if not parts and citation.get('point'):
            parts = re.findall(r'\d+|[a-z]', citation['point'], re.I)
        paragraph = citation.get('paragraph')
        if paragraph is not None and (not parts or parts[0] != str(paragraph)):
            parts.insert(0, str(paragraph))
        if paragraph is not None and citation.get('point'):
            explicit = re.findall(r'\d+|[a-z]', citation['point'], re.I)
            if explicit and explicit[0] == str(paragraph):
                explicit = explicit[1:]
            if len(parts) == 1:
                parts.extend(explicit)
        parts = [p.lower() for p in parts]
        canonical = f'Article {article[1]}' + ''.join(f'({p})' for p in parts)
        # Do not invent paragraph 1, even when the letter is recognizable.
        incomplete = article[1] == '5' and not (
            len(parts) >= 2 and parts[0].isdigit() and len(parts[1]) == 1 and parts[1].isalpha())
        if article[1] == '50':
            incomplete = not (parts and parts[0].isdigit())
    else:
        annex = re.search(r'\bAnnex\s+([IVXLCDM]+)(?:,?\s+(?:point\s+)?(\d+)(?:\(([a-z])\))?)?', label, re.I)
        annex_id = citation.get('annex') or (annex[1] if annex else None)
        if annex_id:
            point = citation.get('point') or ((annex[2] or '') + (f'({annex[3]})' if annex[3] else '') if annex else '')
            parts = re.findall(r'\d+|[a-z]', point, re.I)
            suffix = parts[0] + ''.join(f'({p.lower()})' for p in parts[1:]) if parts else ''
            canonical = f'Annex {annex_id.upper()}' + (f' point {suffix}' if suffix else '')
        else:
            canonical, incomplete = label, True
    result['canonical_citation'] = canonical
    result['citation_incomplete'] = incomplete if supporting else False
    return result


def tier_citation_review_reasons(tier, supporting):
    citations = [canonicalize_citation(c) for c in supporting]
    labels = [c['canonical_citation'] for c in citations]
    if tier == 'PROHIBITED' and not any(re.match(r'^Article 5\(\d+\)\([a-z]\)', c['canonical_citation']) and not c['citation_incomplete'] for c in citations):
        return ['tier_citation_inconsistent:prohibited_without_article_5_paragraph']
    if tier == 'LIMITED_RISK' and not any(re.match(r'^Article 50(?:\(|$)', s) for s in labels):
        return ['tier_citation_inconsistent:limited_without_article_50']
    if tier == 'HIGH_RISK' and not any(re.match(r'^Annex III(?: point|$)|^Article 6\(1\)(?:\(|$)', s) for s in labels):
        return ['tier_citation_inconsistent:high_without_annex_iii_or_article_6_1']
    if tier == 'MINIMAL_RISK' and citations:
        return ['tier_citation_inconsistent:minimal_with_supporting_citation']
    return []
