import importlib.util
from collections import Counter
from pathlib import Path

import pytest

from app.ai_review import ContractReview, grounded_findings, source_quote
from app.analysis import analyze_pages, split_clauses

RUNNER = Path(__file__).resolve().parents[2] / "testing" / "benchmark" / "evaluate.py"
spec = importlib.util.spec_from_file_location("benchmark_runner", RUNNER)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
CASES = benchmark.cases()


def test_benchmark_language_balance_and_independence():
    assert Counter(case["language"] for case in CASES) == {"en": 30, "ar": 30}
    assert len({case["id"] for case in CASES}) == len({case["text"] for case in CASES}) == 60
    assert len({case["scenario"] for case in CASES}) == 15
    pilot = [case for case in CASES if case["id"] in benchmark.PILOT]
    assert Counter(case["language"] for case in pilot) == {"en": 3, "ar": 3}


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_benchmark_evidence_matches_original_clauses(case):
    result = analyze_pages([{"page": 1, "text": case["text"]}], full_text=True)
    sources = {clause["id"]: clause["text"] for clause in result["clauses"]}
    assert case["notes"]
    assert case["contradiction"] == any(point["category"] == "contradiction" for point in case["expected"])
    for point in case["expected"]:
        assert point["risk"] in ("clarify", "concern")
        ids = {ev["clause_id"] for ev in point["evidence"]}
        assert ids and (point["category"] != "contradiction" or len(ids) >= 2)
        for ev in point["evidence"]:
            assert ev["quote"] in sources[ev["clause_id"]]


def test_scoring_distinguishes_citations_from_semantic_label_matches():
    case = next(case for case in CASES if case["id"] == "en-13")
    clauses = analyze_pages([{"page": 1, "text": case["text"]}], full_text=True)["clauses"]
    evidence = [{"page": 1, **item} for item in case["expected"][0]["evidence"]]
    result = {"analysis_method": "ollama_chat", "clauses": clauses, "findings": [
        {"category": "contradiction", "risk": "clarify", "evidence": evidence}
    ]}
    row = benchmark.score(case, result, 1)
    assert row["valid_citations"] == row["citations"] == 2
    assert (row["tp"], row["fp"], row["fn"], row["status"]) == (0, 1, 1, "Partially correct")
    result["analysis_method"] = "local_keyword_rules_prototype"
    row = benchmark.score(case, result, 1)
    assert benchmark.summarize([row])["f1"] is None


def test_mixed_clause_headings_preserve_long_arabic_text_and_numeric_forms():
    rent = "المادة ٣: يسدد المستاجر مبلغ ٤٠٠ رينغيت."
    terms = (
        "البند 4: تحتفظ الادارة بسجل الدفعات. "
        + "ويجوز للطالب طلب بيان الإيجار من المكتب. " * 28
        + "\nالبند 3 يذكر قيمة الإيجار."
    )
    exit_term = "Section ۵: The student may return the key on the final day."
    assert split_clauses("\n".join((rent, terms, exit_term))) == [rent, terms, exit_term]


def test_whole_normalized_pdf_clause_keeps_trailing_original_mark():
    source = "ﻳُﺴﺪَّد\u00a0المبلغُ"
    assert source_quote(source, "يسدد المبلغ", normalize=True) == source


def test_verified_refund_relabels_routine_but_never_hides_explicit_forfeiture():
    ordinary = "The deposit is returned within five days. Deductions are allowed only against documented repairs."
    for text, risk in ((ordinary, "routine"), (ordinary + " It is forfeited on transfer.", "concern")):
        source = {"id": "c-1", "page": 1, "text": text}
        review = ContractReview(findings=[{
            "category": "deposit", "risk": "concern",
            "explanation": {"en": "A refund and deductions are described.", "ar": "يحدد البند طريقة رد التأمين."},
            "landlord_question": {"en": "Could I get a receipt?", "ar": "هل يمكنني الحصول على إيصال؟"},
            "evidence": [{"clause_id": "c-1", "quote": text}],
        }])
        result, = grounded_findings(review, [source], "en", normalize=True)
        assert result["risk"] == risk and result["quote"] == text


@pytest.mark.parametrize("amount,currency,supported", [
    ("١٬٢٧٥", "رينغيت", True),
    ("١٢٧٦", "رينغيت", False),
    ("١٢٧٥", "ريال", False),
])
def test_model_amount_and_currency_must_match_the_source(amount, currency, supported):
    source = {"id": "c-1", "page": 1, "text": "يدفع الطالب 1275 رينغيت عند الاستلام."}
    review = ContractReview(findings=[{
        "category": "fees", "risk": "clarify",
        "explanation": {"en": "Check the move-in charge.", "ar": f"تستحق الرسوم و{amount} {currency} عند الاستلام."},
        "landlord_question": {"en": "What is included?", "ar": "ما الذي يشمله المبلغ؟"},
        "evidence": [{"clause_id": "c-1", "quote": source["text"]}],
    }])
    if supported:
        assert grounded_findings(review, [source], "ar", normalize=True)[0]["quote"] == source["text"]
    else:
        with pytest.raises(ValueError, match="No verified"):
            grounded_findings(review, [source], "ar", normalize=True)


@pytest.mark.parametrize("ids,arabic,expected", [
    (["c-1", "c-2"], "تعارض محتمل: البندان يسندان العبء لطرفين مختلفين.", "contradiction"),
    (["c-1"], "تعارض محتمل: البندان يسندان العبء لطرفين مختلفين.", "maintenance"),
    (["c-1", "c-2"], "لا يوجد تعارض صريح بين البندين.", "maintenance"),
])
def test_conflict_label_requires_two_sources_and_an_affirmative_bilingual_label(ids, arabic, expected):
    sources = [
        {"id": "c-1", "page": 1, "text": "The manager alone replaces a worn window latch."},
        {"id": "c-2", "page": 2, "text": "The resident alone replaces the same worn window latch."},
    ]
    point = {
        "category": "maintenance", "risk": "clarify",
        "explanation": {"en": "Conflict: the two clauses assign the same task to different parties.", "ar": arabic},
        "landlord_question": {"en": "Who replaces the latch?", "ar": "من يستبدل المزلاج؟"},
        "evidence": [{"clause_id": c["id"], "quote": c["text"]} for c in sources if c["id"] in ids],
    }
    result, = grounded_findings(ContractReview(findings=[point]), sources, "ar", normalize=True)
    assert result["category"] == expected
    assert result["risk"] == ("concern" if expected == "contradiction" else "clarify")
