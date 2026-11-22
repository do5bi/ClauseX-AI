import asyncio
import json

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import translation
from app.analysis import extract_clauses
from app.main import app

CLIENT = TestClient(app)
EN = "The tenant shall not pay RM 1,250.50 unless notified on 12 March 2027 with 14 days of notice."
AR = "لا يدفع المستأجر RM ١٬٢٥٠٫٥٠ ما لم يُخطر في ١٢ مارس ٢٠٢٧ بإشعار مدته ١٤ يوماً."


def run(pages, target="auto"):
    return asyncio.run(translation.translate_pages(pages, target))


def mock_translation(monkeypatch, transform):
    calls = []

    async def generate(payload, instructions, schema, *, model=None, max_tokens=None):
        original = json.loads(payload)["source_text"]
        assert model == "qwen3:4b"
        assert schema["required"] == ["translation"]
        assert 120 <= max_tokens <= 120 + translation.FRAGMENT_BYTES
        index = len(calls)
        calls.append(original)
        return json.dumps({"translation": transform(original, index)}, ensure_ascii=False)

    monkeypatch.setattr(translation, "request_ollama_chat", generate)
    return calls


@pytest.mark.parametrize("source,target,output", [(EN, "ar", AR), (AR, "en", EN)])
def test_bidirectional_translation_retains_original_unicode_page_and_id(monkeypatch, source, target, output):
    calls = mock_translation(monkeypatch, lambda *_: output)
    pages = [{"page": 1, "text": ""}, {"page": 2, "text": source}]
    result = run(pages)
    assert result["target_language"] == target
    assert result["pages_processed"] == 2
    assert result["clauses"] == [{**extract_clauses(pages)[0], "translation": output}]
    assert len(calls) == 1


@pytest.mark.parametrize("bad", [
    AR.replace("١٬٢٥٠٫٥٠", "١٬٢٥٠٫٠٥"),
    AR.replace("RM", "USD"),
    AR.replace("مارس", "أبريل"),
    AR.replace("١٢ مارس", "١٤ مارس").replace("١٤ يوماً", "١٢ يوماً"),
    AR.replace("١٤ يوماً", "١٤ أسبوعاً"),
    AR.replace("لا يدفع", "يدفع"),
    AR.replace("ما لم يُخطر", "ويُخطر"),
    EN,
])
def test_model_output_with_unverified_protected_terms_is_rejected(monkeypatch, bad):
    mock_translation(monkeypatch, lambda *_: bad)
    with pytest.raises(translation.TranslationRejected):
        run([{"page": 1, "text": EN}])


def test_prohibition_does_not_match_absence_of_an_obligation():
    source = translation.constraints("The landlord is not required to inspect the room.")
    equivalent = translation.constraints("لا يلزم المؤجر بمعاينة الغرفة.")
    reversed_obligation = translation.constraints("لا يجوز للمؤجر معاينة الغرفة.")
    assert source == equivalent and source != reversed_obligation


def test_signed_currency_and_working_day_distinctions():
    source = translation.constraints("A credit of -RM 50 applies for 5 working days.")
    assert source == translation.constraints("يُطبق رصيد بقيمة RM −٥٠ لمدة ٥ أيام عمل.")
    assert source != translation.constraints("يُطبق رصيد بقيمة RM ٥٠ لمدة ٥ أيام عمل.")
    assert source != translation.constraints("يُطبق رصيد بقيمة RM −٥٠ لمدة ٥ أيام.")


def test_deadline_and_advance_notice_cannot_be_rephrased_as_delays_or_durations():
    refund = translation.constraints("The owner returns the deposit within 8 days.")
    assert refund == translation.constraints("يرد المالك التأمين خلال ٨ أيام.")
    assert refund != translation.constraints("يرد المالك التأمين بعد ٨ أيام.")
    notice = translation.constraints("The student must give 15 days' written notice.")
    assert notice == translation.constraints("يقدم الطالب إشعارا خطيا قبل ١٥ يوما.")
    assert notice == translation.constraints("يقدم الطالب إشعارا خطيا قبل الموعد بـ ١٥ يوما.")
    assert notice != translation.constraints("يقدم الطالب إشعارا خطيا يدوم ١٥ يوما.")
    assert translation.constraints("إشعار خطي قبل 24 ساعة.") == translation.constraints(
        "Give written notice at least 24 hours prior."
    )


def test_currency_code_does_not_make_echoed_arabic_an_english_translation(monkeypatch):
    source = "يدفع المستأجر مبلغ RM 750 عند التسليم."
    mock_translation(monkeypatch, lambda *_: source)
    with pytest.raises(translation.TranslationRejected, match="Wrong target"):
        run([{"page": 1, "text": source}])


def test_mixed_source_can_use_either_explicit_target(monkeypatch):
    pages = [{"page": 1, "text": "The tenant must return the keys.\n\nيتحمل المالك مسؤولية إصلاح الباب."}]
    mock_translation(monkeypatch, lambda _, index: ("The tenant must return the keys.", "The owner must repair the door.")[index])
    result = run(pages, "en")
    assert result["mixed"] and result["target_language"] == "en"
    assert result["clauses"][1]["text"] == "يتحمل المالك مسؤولية إصلاح الباب."


@pytest.mark.parametrize("malformed", ['{}', '{"translation": "one", "translation": "two"}',
                                      '{"translation": "one", "clause_id": "c-99"}'])
def test_missing_duplicate_and_unknown_response_fields_fail(monkeypatch, malformed):
    async def generate(*args, **kwargs):
        return malformed

    monkeypatch.setattr(translation, "request_ollama_chat", generate)
    with pytest.raises(ValueError):
        run([{"page": 1, "text": EN}])


def test_responses_remain_bound_to_their_original_clause_and_page(monkeypatch):
    mock_translation(monkeypatch, lambda _, index: AR if index == 0 else AR.replace("١٤", "٣٠"))
    pages = [{"page": 1, "text": EN}, {"page": 2, "text": EN.replace("14", "30")}]
    actual = run(pages)["clauses"]
    assert [(item["id"], item["page"], item["translation"]) for item in actual] == [
        ("c-1", 1, AR), ("c-2", 2, AR.replace("١٤", "٣٠"))
    ]


def test_batching_translates_every_fragment_without_changing_clause_boundaries(monkeypatch):
    sentence = "The tenant keeps the inventory for the landlord. "
    source = sentence * 125
    calls = mock_translation(monkeypatch, lambda *_: "يحتفظ المستأجر بقائمة الجرد للمؤجر.")
    result = run([{"page": 3, "text": source}])
    assert len(calls) > 1
    assert all(len(part.encode()) <= translation.FRAGMENT_BYTES for part in calls)
    assert " ".join(calls) == source.strip()
    clause, = result["clauses"]
    assert clause["id"] == "c-1" and clause["page"] == 3 and clause["text"] == source.strip()
    assert len(clause["translation"].splitlines()) == len(calls)


def test_pdf_translation_endpoint_keeps_extracted_source_and_explicit_target(monkeypatch):
    mock_translation(monkeypatch, lambda *_: AR)
    with pymupdf.open() as pdf:
        pdf.new_page()
        page = pdf.new_page()
        page.insert_text((36, 72), EN, fontsize=8)
        original = page.get_text().strip()
        data = pdf.tobytes()
    files = {"file": ("fictional.pdf", data, "application/pdf")}
    result = CLIENT.post("/api/translate-file?target=ar", files=files)
    assert result.status_code == 200
    assert result.json()["clauses"][0] == {"id": "c-1", "page": 2, "text": original, "translation": AR}
    response = CLIENT.post("/api/translate-file?target=en", files=files)
    assert response.status_code == 422 and response.json()["detail"] == "translation_same_language"


@pytest.mark.parametrize("failure,status,detail", [
    (httpx.ReadTimeout("slow"), 504, "translation_timeout"),
    (httpx.ConnectError("offline"), 503, "translation_unavailable"),
    (ValueError("bad response"), 422, "translation_unverified"),
])
def test_model_failure_returns_clear_error_without_partial_translation(monkeypatch, failure, status, detail):
    async def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(translation, "request_ollama_chat", fail)
    response = CLIENT.post("/api/translate-sample?lang=en&target=ar")
    assert response.status_code == status and response.json() == {"detail": detail}
    assert CLIENT.get("/api/sample?lang=en").status_code == 200
