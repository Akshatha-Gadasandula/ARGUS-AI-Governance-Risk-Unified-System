"""Display unverified regulatory references without invented section numbers."""

RBI_NOT_ASSESSED = "RBI: not assessed (no corpus indexed)"


def alert_reference_text(reference: str) -> str:
    parts = []
    for part in reference.split(";"):
        part = part.strip()
        lower = part.lower()
        if "rbi" in lower and any(
            marker in lower for marker in ("unverified", "corpus", "not assessed")
        ):
            part = RBI_NOT_ASSESSED
        parts.append(part)
    return "; ".join(parts)
