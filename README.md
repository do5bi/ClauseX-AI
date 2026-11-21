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

The backend verifies quotes against the extracted clauses. When the provider
fails, the result cannot be verified, or the agreement exceeds the model input
limit, the workspace identifies the keyword fallback. The calculator runs in the browser.
