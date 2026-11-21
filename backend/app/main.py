from io import BytesIO
from typing import Literal
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pymupdf
from .analysis import analyze_pages
from .ai_review import get_provider, review_pages
from .sample_agreements import DEFAULT_SAMPLE_ID, list_samples, sample_pages, display_sample_text

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 25
app = FastAPI(title="ClauseX AI API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-ClauseX-AI-Consent"],
)

class TextRequest(BaseModel):
    text: str = Field(min_length=10, max_length=100000)

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local_prototype"}

@app.get("/api/review-config")
def review_config():
    return {"provider": get_provider()}

SampleId = Literal["shared_house", "deposit_dispute", "early_exit", "house_rules"]

@app.get("/api/samples")
def get_samples(lang: Literal["en", "ar"] = "en"):
    return {"samples": list_samples(lang), "default_sample_id": DEFAULT_SAMPLE_ID}

@app.get("/api/sample")
def get_sample(lang: Literal["en", "ar"] = "en", sample_id: SampleId = DEFAULT_SAMPLE_ID):
    pages = sample_pages(sample_id, lang)
    return {"sample_id": sample_id, "text": display_sample_text(pages, lang),
            **analyze_pages(pages)}

@app.post("/api/analyze-sample")
async def analyze_sample(lang: Literal["en", "ar"] = "en", sample_id: SampleId = DEFAULT_SAMPLE_ID,
                         x_clausex_ai_consent: str = Header(default="")):
    return await review_pages(sample_pages(sample_id, lang), x_clausex_ai_consent, lang)

@app.post("/api/analyze-text")
async def analyze_text(req: TextRequest, lang: Literal["en", "ar"] = "en",
                       x_clausex_ai_consent: str = Header(default="")):
    return await review_pages([{"page": 1, "text": req.text}], x_clausex_ai_consent, lang)

@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...), lang: Literal["en", "ar"] = "en",
                       x_clausex_ai_consent: str = Header(default="")):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Only text-based PDF files are supported in Sprint 1.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File exceeds the 8 MB limit.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "File does not have a valid PDF signature.")
    try:
        with pymupdf.open(stream=BytesIO(data), filetype="pdf") as doc:
            if doc.is_encrypted:
                raise HTTPException(422, "Encrypted PDFs are not supported.")
            if len(doc) > MAX_PAGES:
                raise HTTPException(413, "Maximum 25 pages per document.")
            pages = [{"page": i + 1, "text": doc[i].get_text("text")} for i in range(len(doc))]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "Cannot read this PDF file.")
    if not any(p["text"].strip() for p in pages):
        raise HTTPException(422, "This PDF has no selectable text. OCR support is planned.")
    return await review_pages(pages, x_clausex_ai_consent, lang)
