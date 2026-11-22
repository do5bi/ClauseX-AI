"""Local extractive rules for the Sprint 1 demonstration; not legal/AI analysis."""
import re
import unicodedata
from typing import Any

# Explain that findings indicate topics to review, NOT legal invalidity.
PATTERNS = [
    ("deposit", "high", r"\b(?:security\s+deposit|deposit\s+(?:shall|may)\s+be\s+(?:forfeit|retain)|forfeit(?:ed|ure)?\s+(?:the\s+)?deposit)\b", "Potential deposit-related obligation"),
    ("termination", "review", r"\b(?:early\s+terminat(?:ion|e)|terminat(?:ion|e)\s+early|break\s+(?:the\s+)?lease|notice\s+period)\b", "Review early termination and notice requirements"),
    ("fees", "review", r"\b(?:late\s+fee|penalt(?:y|ies)|additional\s+charge|administration\s+fee)\b", "Review additional fees or penalties"),
    ("entry", "review", r"\b(?:landlord\s+may\s+enter|right\s+to\s+enter|access\s+the\s+premises)\b", "Review landlord access provisions"),
    ("maintenance", "review", r"\b(?:repair(?:s)?\s+(?:at\s+the\s+)?tenant|tenant\s+(?:is\s+)?responsible\s+for\s+(?:all\s+)?repair|maintenance\s+cost)\b", "Review maintenance or repair responsibilities"),
]

ARABIC_PATTERNS = [
    ("deposit", r"(?:مبلغ|وديعة)\s+(?:ال)?ت[أا]مين|الت[أا]مين\s+(?:النقدي|المسترد)", "مبلغ التأمين"),
    ("termination", r"[إا]نهاء\s+(?:العقد|عقد\s+الإيجار)\s+(?:مبكر[ًا]*|قبل\s+انتهاء)|ال[إا]نهاء\s+المبكر|(?:مدة|فترة|مهلة)\s+ال[إا]شعار", "الإنهاء ومدة الإشعار"),
    ("fees", r"(?:رسوم|غرامة|غرامات)\s+(?:(?:ال)?ت[أا]خير|إضافية)", "رسوم إضافية"),
    ("entry", r"(?:يجوز|يحق)\s+للمؤجر\s+(?:دخول|الدخول)|دخول\s+(?:المؤجر|المالك)", "دخول المؤجر"),
    ("maintenance", r"(?:تكاليف|مسؤولية|أعمال)\s+الصيانة|(?:صيانة|إصلاح)\s+(?:المسكن|الأعطال)", "مسؤوليات الصيانة"),
]


def arabic_matches(clause: str):
    if not re.search(r"[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]", clause):
        return
    # Match contextual letter forms and vocalized text while quoting the original PDF.
    letters = []
    offsets = []
    for offset, char in enumerate(clause):
        for letter in unicodedata.normalize("NFKC", char):
            if letter == "ـ" or unicodedata.combining(letter):
                continue
            letters.append(letter)
            offsets.append(offset)
    searchable = "".join(letters)
    for category, pattern, title in ARABIC_PATTERNS:
        match = re.search(pattern, searchable)
        if match:
            yield category, title, offsets[match.start()], offsets[match.end() - 1] + 1


def split_clauses(text: str) -> list[str]:
    """Find clause boundaries without changing the source text."""
    # PDF extractors can put an RTL clause number on a line of its own.
    # A delimiter distinguishes a named heading from a reference inside a clause.
    named = r"(?:clause|section|article|البند|المادة)[^\S\n]+\d+[^\S\n]*[.):：]"
    numbered = r"\d+[^\S\n]*(?:\n[^\S\n]*)?[.)]\s+"
    boundary = rf"\n\s*\n|(?=\n\s*(?:{named}|{numbered}))"
    blocks = [block.strip() for block in re.split(boundary, text, flags=re.IGNORECASE) if block.strip()]
    return blocks if blocks else ([text.strip()] if text.strip() else [])


def extract_clauses(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clauses = []
    for page in pages:
        for text in split_clauses(page["text"]):
            clauses.append({"id": f"c-{len(clauses) + 1}", "page": page["page"], "text": text})
    return clauses


def analyze_pages(pages: list[dict[str, Any]], *, full_text=False) -> dict[str, Any]:
    findings = []
    segments = []
    for segment in extract_clauses(pages):
        segment_id, page, clause = segment["id"], segment["page"], segment["text"]
        segments.append({**segment, "text": clause if full_text else clause[:5000]})
        for kind, severity, pattern, headline in PATTERNS:
            match = re.search(pattern, clause, flags=re.IGNORECASE)
            if not match:
                continue
            # Mention of a routine refundable deposit is not, by itself, high risk.
            context_risk = bool(re.search(
                r"\b(?:forfeit(?:ed|ure)?|retain\s+(?:the\s+)?(?:full|entire)|non[- ]refundable)\b",
                clause, flags=re.IGNORECASE
            ))
            level = ("high" if context_risk else "review") if kind == "deposit" else severity
            findings.append({
                "id": f"f-{len(findings)+1}",
                "clause_id": segment_id,
                "page": page,
                "category": kind,
                "level": level,
                "title": headline,
                "quote": clause[:500],
                "matched_phrase": match.group(0),
                "explanation": "Keyword-based review marker only. Check the full clause and applicable rules; this is not a determination of legal validity.",
            })
        for category, title, start, end in arabic_matches(clause):
            quote_start = max(0, start - 180)
            findings.append({
                "id": f"f-{len(findings)+1}",
                "clause_id": segment_id,
                "page": page,
                "category": category,
                "level": "review",
                "title": title,
                "quote": clause[quote_start:max(quote_start + 500, end)],
                "matched_phrase": clause[start:end],
                "explanation": "وردت هذه العبارة في نص البند. راجع سياقها لفهم الشروط المرتبطة بها.",
            })
    return {
        "clauses": segments,
        "findings": findings,
        "analysis_method": "local_keyword_rules_prototype",
        "disclaimer": "Demo prototype only; no legal opinion or AI-model analysis. A missing flag is not proof of contract safety.",
        "pages_processed": len(pages),
    }
