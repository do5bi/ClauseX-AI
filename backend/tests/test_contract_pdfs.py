import re
import unicodedata
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.ai_review import normalize_ollama_clause, source_quote
from app.main import app
from app.sample_agreements import sample_pages

FIXTURES = Path(__file__).resolve().parents[2] / "testing" / "contracts"
CLIENT = TestClient(app)


def comparable(text):
    # PDF fonts can map the same visible punctuation or vowel mark differently.
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "-")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


@pytest.mark.parametrize("scenario", ("shared_house", "early_exit", "house_rules"))
@pytest.mark.parametrize("lang", ("en", "ar"))
def test_fictional_pdf_extracts_and_groups_all_clauses(scenario, lang):
    path = FIXTURES / f"{scenario}-{lang}.pdf"
    data = path.read_bytes()
    with pymupdf.open(stream=data, filetype="pdf") as document:
        assert len(document) == 2
        extracted = [page.get_text() for page in document]
    result = CLIENT.post(
        f"/api/analyze-file?lang={lang}", files={"file": (path.name, data, "application/pdf")}
    ).json()
    assert result["pages_processed"] == 2
    marker = r"^(?:Clause\s+\d+|\d+\s*\.)"
    clauses = [clause for clause in result["clauses"] if re.match(marker, clause["text"])]
    assert len(clauses) == 12
    sources = {clause["id"]: clause for clause in result["clauses"]}
    assert result["findings"]
    for finding in result["findings"]:
        source = sources[finding["clause_id"]]
        assert source["page"] == finding["page"]
        assert finding["quote"] in source["text"] in extracted[source["page"] - 1]
    for page in sample_pages(scenario, lang):
        original = [line for line in page["text"].splitlines() if re.match(marker, line)]
        searchable = comparable(normalize_ollama_clause(extracted[page["page"] - 1])[0])
        for line in original:
            # Ignore the clause number, whose PDF glyph may wrap onto its own line.
            body = re.sub(r"^.*?\.\s+", "", line, count=1)
            assert comparable(body) in searchable


def test_model_quote_with_layout_spacing_restores_exact_pdf_text():
    source = "يدفع الطالب مبلغ\n  التأمين عند تسلم الغرفة."
    assert source_quote(source, "مبلغ التأمين", True) == "مبلغ\n  التأمين"
    with pytest.raises(ValueError):
        source_quote(source, "مبلغ الإيجار", True)
