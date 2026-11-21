"""Fictional bilingual leases: demo/test cases, not legal templates or training data."""
import json
from pathlib import Path

_SAMPLE_DATA = json.loads(Path(__file__).with_name("sample_agreements.json").read_text(encoding="utf-8"))
SAMPLES = _SAMPLE_DATA["samples"]
DEFAULT_SAMPLE_ID = "shared_house"


def list_samples(lang: str) -> list[dict]:
    return [
        {"id": key, "title": data[lang]["title"], "description": data[lang]["description"]}
        for key, data in SAMPLES.items()
    ]


def sample_pages(sample_id: str, lang: str) -> list[dict]:
    data = SAMPLES[sample_id][lang]["pages"]
    return [{"page": index + 1, "text": text} for index, text in enumerate(data)]


def display_sample_text(pages: list[dict], lang: str) -> str:
    label = "صفحة" if lang == "ar" else "Page"
    return "\n\n".join(f"— {label} {page['page']} —\n\n{page['text']}" for page in pages)
