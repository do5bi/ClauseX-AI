# ClauseX-AI
ClauseX AI helps students review rental agreements in English and Arabic. The workspace
includes local Ollama review, a keyword fallback, and a financial scenario calculator.

### Local AI review with Ollama

Install `backend/requirements.txt`, start Ollama, and run `ollama pull qwen3:4b`.
Copy `backend/.env.example` to `backend/.env` and restart FastAPI. The defaults
are `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, and
`OLLAMA_MODEL=qwen3:4b`. The Ollama URL must be a local loopback address.
Set `OLLAMA_NUM_GPU=0` if the GPU runner fails to load the model.

With Ollama, PDF review sends extracted clauses to the model on this computer.
Opening a sample initially shows keyword results. Use the review button in the
workspace to request an AI review of that sample.

For optional OpenAI review, set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and
optionally `OPENAI_MODEL` in the Git-ignored backend `.env`. The consent checkbox
allows one request to send extracted text, clause IDs, and pages to OpenAI with
`store=False`.

Ollama selects clause IDs from a constrained list. The backend copies evidence from
the matching source clauses and derives the page numbers. It checks quotes supplied
by OpenAI against the same source. When the provider
fails, the result cannot be verified, or the agreement exceeds the model input
limit, the workspace identifies the keyword fallback. The calculator runs in the browser.

### Realistic bilingual sample agreements

The Review workspace now includes a scenario selector with four fictional, multi-page
student lease agreements in **English and Arabic**:

1. Shared student house — balanced refundable-deposit and utility terms.
2. Deposit and deductions — ambiguous deductions, fees, and delayed refunds.
3. Early exit — potentially conflicting notice periods and renewal wording.
4. House rules — possible conflicts around entry, repairs, and shared bills.

Use **Try sample agreement** after choosing a scenario. Switching the interface language
while a sample is open loads that scenario's matching-language document; it does **not**
translate PDFs uploaded by users. Uploaded contracts stay in their source language.

The source text and two-page structure live in `backend/app/sample_agreements.json`.
`GET /api/samples?lang=ar` lists scenarios; `GET /api/sample?lang=ar&sample_id=early_exit`
loads a source-linked preview, and `POST /api/analyze-sample?lang=ar&sample_id=early_exit`
performs model review with the same local/remote consent header as file uploads.

The scenario corpus is for demonstrations, regression tests, and in-context prompt
calibration. It does **not** train or fine-tune Ollama. The contracts are fictional
examples, **not legal templates**. AI explanations must be checked against the source
text; correct quotations do not guarantee legally correct interpretation.

The six selectable-text fixtures in `testing/contracts` cover the shared house,
early exit, and house rules in both languages. Each has two pages. To regenerate
them from the catalog, run `python testing/contracts/generate.py C:/Windows/Fonts`
with the backend dependencies installed. The generator accepts a font directory
containing Arial regular and bold, which it embeds in the PDFs.

Run `cd backend && python -m pytest -q` and
`cd frontend && npm ci && npm run build` to verify the current source.
