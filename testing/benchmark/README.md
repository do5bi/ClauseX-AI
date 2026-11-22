# ClauseX bilingual accuracy benchmark

`cases.jsonl` contains 60 independent fictional rental excerpts, split evenly between
English and Arabic. Each line records the original text, expected attention findings,
literal source excerpts and clause IDs, a contradiction flag, and an annotation rationale.
The examples describe possible contract issues and clarification needs. They make no
determinations about enforceability. They are evaluation fixtures and are never sent
to the model as demonstrations.

From the repository root, with the backend's development dependencies installed and
local Ollama running, use:

```powershell
backend/.venv/Scripts/python.exe testing/benchmark/evaluate.py testing/benchmark/run.json
```

The default pilot is fixed to three English and three Arabic cases. Use `--ids`
for a targeted check or `--all` for the full CPU-intensive evaluation. The runner
sends only each original excerpt and language through the actual text endpoint.
It records model output, source citations, methods, and wall-clock timings. Keep
evaluation result files separate from the production prompt.

## Scoring

- A true positive is one attention finding with the expected category and risk and
  all required, verified source clause IDs. Each expected finding is matched once.
- A wrong risk, category, or incomplete cited scope can count as both a false
  positive and a false negative. Routine summaries are optional and excluded from
  the attention metrics. Their citations are still checked.
- Contradiction detection measures the presence or absence of the category per
  case. Finding-level scoring additionally checks risk and the source clause IDs.
- Citation validity checks exact quote containment and page equality. Semantic
  correctness requires comparing the interpretation with the case rationale.
- Ambiguous cases are marked **Uncertain** and excluded from aggregate accuracy.
  Fallback outcomes are **Not evaluated** for model accuracy, and still count
  toward the fallback frequency and wall-clock mean. Unattempted cases are also
  **Not evaluated**. A zero denominator is reported as **Not evaluated**.
