"""Local extractive rules for the Sprint 1 demonstration; not legal/AI analysis."""
import re
from typing import Any

# Explain that findings indicate topics to review, NOT legal invalidity.
PATTERNS = [
    ("deposit", "high", r"\b(?:security\s+deposit|deposit\s+(?:shall|may)\s+be\s+(?:forfeit|retain)|forfeit(?:ed|ure)?\s+(?:the\s+)?deposit)\b", "Potential deposit-related obligation"),
    ("termination", "review", r"\b(?:early\s+terminat(?:ion|e)|terminat(?:ion|e)\s+early|break\s+(?:the\s+)?lease|notice\s+period)\b", "Review early termination and notice requirements"),
    ("fees", "review", r"\b(?:late\s+fee|penalt(?:y|ies)|additional\s+charge|administration\s+fee)\b", "Review additional fees or penalties"),
    ("entry", "review", r"\b(?:landlord\s+may\s+enter|right\s+to\s+enter|access\s+the\s+premises)\b", "Review landlord access provisions"),
    ("maintenance", "review", r"\b(?:repair(?:s)?\s+(?:at\s+the\s+)?tenant|tenant\s+(?:is\s+)?responsible\s+for\s+(?:all\s+)?repair|maintenance\s+cost)\b", "Review maintenance or repair responsibilities"),
]


def split_clauses(text: str) -> list[str]:
    """Split demo inputs into clauses/paragraphs without inventing any text."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n|(?=\n\s*(?:Clause\s+\d+|\d+[.)]\s+))", text) if b.strip()]
    return blocks if blocks else ([text.strip()] if text.strip() else [])


def analyze_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    segments = []
    for page in pages:
        for clause in split_clauses(page["text"]):
            segment_id = f"c-{len(segments)+1}"
            segment = {"id": segment_id, "page": page["page"], "text": clause[:5000]}
            segments.append(segment)
            for kind, severity, pattern, headline in PATTERNS:
                match = re.search(pattern, clause, flags=re.IGNORECASE)
                if not match:
                    continue
                findings.append({
                    "id": f"f-{len(findings)+1}",
                    "clause_id": segment_id,
                    "page": page["page"],
                    "category": kind,
                    "level": severity,
                    "title": headline,
                    "quote": clause[:500],
                    "matched_phrase": match.group(0),
                    "explanation": "Keyword-based review marker only. Check the full clause and applicable rules; this is not a determination of legal validity.",
                })
    return {
        "clauses": segments,
        "findings": findings,
        "analysis_method": "local_keyword_rules_prototype",
        "disclaimer": "Demo prototype only; no legal opinion or AI-model analysis. A missing flag is not proof of contract safety.",
        "pages_processed": len(pages),
    }
