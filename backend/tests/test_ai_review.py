import json

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from app import ai_review
from app.main import app

client = TestClient(app)
CONSENT = {"X-ClauseX-AI-Consent": "send-to-openai"}
TEXT = "The notice period is 30 days.\n\nThe notice period is 60 days."
POINT = {
    "category": "contradiction",
    "explanation": {"en": "The notice periods differ.", "ar": "تختلف مدتا الإشعار."},
    "landlord_question": {"en": "Which period applies?", "ar": "أي مدة تنطبق؟"},
    "evidence": [{"clause_id": "c-1", "quote": "30 days"}, {"clause_id": "c-2", "quote": "60 days"}],
}


def mock_provider(monkeypatch, content, status=200, response_status="completed"):
    requests = []

    def respond(request):
        assert request.url.path == "/v1/responses"
        requests.append(json.loads(request.content))
        return httpx.Response(status, json={
            "id": "resp_test", "object": "response", "status": response_status,
            "output": [{"type": "message", "role": "assistant",
                        "content": [{"type": "output_text", "text": content}]}],
        })

    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-only")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setattr(ai_review, "AsyncOpenAI", lambda **kwargs: AsyncOpenAI(
        **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond))))
    return requests


def test_no_consent_or_key_never_calls_provider(monkeypatch):
    calls = mock_provider(monkeypatch, "")
    client.get("/api/sample?lang=ar", headers=CONSENT)
    for headers in ({}, {"X-ClauseX-AI-Consent": "false"}):
        result = client.post("/api/analyze-text", json={"text": TEXT}, headers=headers).json()
        assert result["analysis_method"] == "local_keyword_rules_prototype"
        assert "fallback_reason" not in result
    monkeypatch.delenv("OPENAI_API_KEY")
    result = client.post("/api/analyze-text", json={"text": TEXT}, headers=CONSENT).json()
    assert result["fallback_reason"] == "unavailable"
    assert not calls


def test_sdk_structured_review_uses_both_cited_clauses(monkeypatch):
    calls = mock_provider(monkeypatch, json.dumps({"findings": [POINT]}))
    result = client.post("/api/analyze-text?lang=ar", json={"text": TEXT}, headers=CONSENT).json()
    assert result["analysis_method"] == "openai_responses"
    finding, = result["findings"]
    assert finding["explanation"] == POINT["explanation"]["ar"]
    assert finding["question"] == POINT["landlord_question"]
    assert finding["evidence"] == [dict(item, page=1) for item in POINT["evidence"]]
    request, = calls
    assert request["store"] is False
    assert request["text"]["format"]["strict"] is True
    assert json.loads(request["input"]) == result["clauses"]


def test_arabic_quote_after_local_preview_limit(monkeypatch):
    phrase = "يعاد مبلغ التأمين بعد تسلّم الغرفة."
    text = "نص العقد " * 700 + phrase
    point = {
        "category": "deposit",
        "explanation": {"en": "The deposit is returned after handover.", "ar": "يُردّ التأمين بعد تسليم الغرفة."},
        "landlord_question": {"en": "When will I receive it?", "ar": "متى أستلم المبلغ؟"},
        "evidence": [{"clause_id": "c-1", "quote": phrase}],
    }
    mock_provider(monkeypatch, json.dumps({"findings": [point]}))
    result = client.post("/api/analyze-text?lang=ar", headers=CONSENT, json={"text": text}).json()
    assert result["analysis_method"] == "openai_responses"
    finding, = result["findings"]
    assert finding["quote"] == phrase and finding["page"] == 1
    assert finding["explanation"] == point["explanation"]["ar"]


@pytest.mark.parametrize("content,status,completion,reason", [
    ("broken JSON", 200, "completed", "unverified"),
    ('{"findings":[{}]}', 200, "completed", "unverified"),
    ('{"findings":[]}', 200, "incomplete", "unverified"),
    ("", 429, "failed", "limit"),
    ("", 500, "failed", "unavailable"),
])
def test_failed_review_returns_original_keyword_findings(monkeypatch, content, status, completion, reason):
    mock_provider(monkeypatch, content, status, completion)
    result = client.post("/api/analyze-text", json={"text": TEXT}, headers=CONSENT).json()
    local = client.post("/api/analyze-text", json={"text": TEXT}).json()
    assert result == {**local, "fallback_reason": reason}


@pytest.mark.parametrize("citations", [
    [],
    [{"clause_id": "c-1", "quote": "30 days"}],
    [{"clause_id": "c-1", "quote": "30 days"}, {"clause_id": "c-2", "quote": "invented"}],
    [{"clause_id": "c-1", "quote": "30 days"}, {"clause_id": "c-999", "quote": "60 days"}],
])
def test_ungrounded_claims_are_rejected(monkeypatch, citations):
    point = {**POINT, "evidence": citations}
    mock_provider(monkeypatch, json.dumps({"findings": [point]}))
    result = client.post("/api/analyze-text", headers=CONSENT, json={"text": TEXT}).json()
    assert result["fallback_reason"] == "unverified"
    assert all(f["category"] != "contradiction" for f in result["findings"])


def test_mixed_review_returns_only_verified_findings(monkeypatch):
    invalid = {**POINT, "evidence": [{"clause_id": "c-1", "quote": "invented"}]}
    mock_provider(monkeypatch, json.dumps({"findings": [invalid, {**POINT, "risk": "concern"}]}))
    result = client.post("/api/analyze-text", headers=CONSENT, json={"text": TEXT}).json()
    assert result["analysis_method"] == "openai_responses"
    assert result["omitted_findings"] == 1
    finding, = result["findings"]
    assert finding["risk"] == "concern" and finding["level"] == "high"
    assert [entry["quote"] for entry in finding["evidence"]] == ["30 days", "60 days"]


def test_ollama_restores_source_glyphs_and_blocks_external_consent(monkeypatch):
    original_quote = "ﻣﺒﻠﻎ\u00a0ﺍﻟﺘﺄﻣﻴﻦ"
    original = f"{original_quote} عند تسلم الغرفة."
    point = {**POINT, "category": "deposit",
             "evidence": [{"clause_id": "c-1", "quote": "مبلغ التأمين"}]}
    calls = []

    async def fake_chat(payload):
        calls.append(json.loads(payload))
        return ai_review.ContractReview(findings=[point])

    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(ai_review, "request_ollama_review", fake_chat)
    assert client.get("/api/review-config").json() == {"provider": "ollama"}
    result = client.post("/api/analyze-text?lang=ar", json={"text": original}, headers=CONSENT).json()
    assert result["fallback_reason"] == "unavailable" and not calls
    result = client.post("/api/analyze-text?lang=ar", json={"text": original},
                         headers={"X-ClauseX-AI-Consent": "run-local"}).json()
    assert result["analysis_method"] == "ollama_chat"
    assert result["findings"][0]["quote"] == original_quote
    assert calls[0][0]["text"].startswith("مبلغ التأمين")


def test_ollama_sample_review_retains_second_page_citation(monkeypatch):
    from app.analysis import analyze_pages
    from app.sample_agreements import sample_pages

    pages = sample_pages('deposit_dispute', 'ar')
    clauses = analyze_pages(pages, full_text=True)['clauses']
    cited = next(c for c in clauses if 'غرامة تأخير' in c['text'])
    assert cited['page'] == 2
    quote = 'غرامة تأخير'
    calls = []

    async def fake_chat(payload):
        calls.append(json.loads(payload))
        return ai_review.ContractReview(findings=[{
            'category': 'fees',
            'explanation': {'en': 'Ask how the daily charge is capped.',
                            'ar': 'اسأل عن الحد الأقصى للغرامة اليومية.'},
            'landlord_question': {'en': 'Is there a cap on the late fee?',
                                  'ar': 'هل يوجد سقف لغرامة التأخير؟'},
            'evidence': [{'clause_id': cited['id'], 'quote': quote}],
        }])

    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    monkeypatch.setattr(ai_review, 'request_ollama_review', fake_chat)
    response = client.post('/api/analyze-sample?lang=ar&sample_id=deposit_dispute',
                           headers={'X-ClauseX-AI-Consent': 'run-local'})
    assert response.status_code == 200
    result = response.json()
    assert result['analysis_method'] == 'ollama_chat'
    finding, = result['findings']
    assert finding['page'] == 2
    assert finding['quote'] == quote
    assert finding['evidence'][0]['clause_id'] == cited['id']
    assert calls[0][len(clauses)-1]['page'] == 2


def test_ollama_chat_constrains_ids_and_copies_original_conflicting_clauses(monkeypatch):
    client_type = httpx.AsyncClient

    def respond(request):
        payload = json.loads(request.content)
        ids = payload["format"]["$defs"]["OllamaPoint"]["properties"]["clause_ids"]["items"]["enum"]
        assert ids == ["c-1", "c-2"]
        point = {key: value for key, value in POINT.items() if key != "evidence"}
        point.update(risk="concern", clause_ids=ids)
        return httpx.Response(200, json={"done": True, "done_reason": "stop",
            "message": {"content": json.dumps({"findings": [point]})}})

    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(ai_review.httpx, "AsyncClient", lambda **kwargs: client_type(
        **kwargs, transport=httpx.MockTransport(respond)))
    result = client.post("/api/analyze-text", json={"text": TEXT},
                         headers={"X-ClauseX-AI-Consent": "run-local"}).json()
    assert result["analysis_method"] == "ollama_chat"
    finding, = result["findings"]
    assert finding["level"] == "high"
    assert [item["quote"] for item in finding["evidence"]] == TEXT.split("\n\n")
