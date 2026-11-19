from io import BytesIO
from typing import Literal
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pymupdf
from .analysis import analyze_pages

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 25
SAMPLE = """STUDENT TENANCY AGREEMENT

Clause 1. Monthly rent is RM 1,000, due on the first day of each month.

Clause 2. Tenant shall pay a security deposit of RM 2,000. The landlord may retain the full security deposit if the tenancy is terminated early.

Clause 3. Tenant must provide 60 days written notice before early termination.

Clause 4. A late fee of RM 100 may apply after seven days of non-payment.

Clause 5. The landlord may enter the premises after prior written notice for necessary maintenance.

Clause 6. Normal wear and tear is excluded from tenant repair costs.
"""

ARABIC_SAMPLE = """عقد إيجار سكن طلابي

١. يستأجر الطالب غرفة مفروشة خلال العام الدراسي. يبلغ الإيجار الشهري ١٬٠٠٠ رينغيت ماليزي، ويُدفع في اليوم الأول من كل شهر.

٢. يدفع الطالب مبلغ التأمين وقدره ٢٬٠٠٠ رينغيت. يردّ المؤجر المبلغ بعد تسلّم الغرفة، ويبيّن كتابةً أي خصم مقابل ضرر يتجاوز الاستهلاك المعتاد.

٣. يجوز للطالب إنهاء العقد قبل انتهاء مدته بإرسال إشعار خطي إلى المؤجر. مدة الإشعار ستون يومًا، ويلتزم الطالب بدفع الإيجار خلالها.

٤. إذا مضت سبعة أيام على موعد السداد، تُضاف رسوم التأخير وقدرها ١٠٠ رينغيت عن الدفعة المتأخرة.

٥. يجوز للمؤجر دخول الغرفة لإجراء إصلاح ضروري بعد الاتفاق مع الطالب على الموعد وإخطاره كتابةً قبل الزيارة بيوم واحد على الأقل.

٦. يتحمل المؤجر تكاليف الصيانة الدورية وإصلاح الأعطال الناتجة عن الاستهلاك المعتاد. وعلى الطالب الإبلاغ عن الأعطال فور ملاحظتها وتحمل تكلفة إصلاح ما يتلفه بسوء الاستخدام."""

app = FastAPI(title="ClauseX Starter API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class TextRequest(BaseModel):
    text: str = Field(min_length=10, max_length=100000)

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local_prototype"}

@app.get("/api/sample")
def get_sample(lang: Literal["en", "ar"] = "en"):
    text = ARABIC_SAMPLE if lang == "ar" else SAMPLE
    return {"text": text, **analyze_pages([{"page": 1, "text": text}])}

@app.post("/api/analyze-text")
def analyze_text(req: TextRequest):
    return analyze_pages([{"page": 1, "text": req.text}])

@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...)):
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
    return analyze_pages(pages)
