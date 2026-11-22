# Live Ollama accuracy pilot

Baseline: repository revision `eef703f`, measured before production changes. Final
run: revised prompt, parser, risk labels, and cited monetary checks. Both runs
used the same six excerpts, local Ollama with `qwen3:4b`, CPU inference, and the
FastAPI text route. Run order was EN-01, EN-13, EN-19, AR-02, AR-07, AR-13.
Results and model output are saved in [baseline.json](baseline.json) and
[after.json](after.json). The other 54 cases have deterministic fixture and
source checks. Their live inference is **Not evaluated**.

| Pilot metric | Baseline | Final |
|---|---:|---:|
| Live responses scored | 4 / 6 | 5 / 6 |
| Finding precision | 33.3% | 100% |
| Finding recall | 50.0% | 100% |
| Finding F1 | 40.0% | 100% |
| False positives on scored cases | 2 | 0 |
| False negatives on scored cases | 1 | 0 |
| Contradiction presence or absence on scored cases | 4 / 4 | 5 / 5 |
| Exact quote and page validity | 5 / 5 | 7 / 7 |
| Fallback frequency | 2 / 6 | 1 / 6 |
| Mean wall time across all attempts | 30.32 s | 28.87 s |

The 100% scores apply to the deterministic benchmark criteria on the five
live responses. They do not measure translation fluency or guarantee legal or
semantic correctness. On the four cases that yielded live model output in both
runs, F1 rose from 40.0% to 100%. Treating fallback cases as missed expected
findings, recall was 25.0% before and 75.0% after, with F1 of 28.6% and 85.7%.
For the two expected contradictions, the model surfaced both after the changes.
It surfaced only the English one in the baseline, and that finding had the
wrong risk label.

| Language | Live cases before → after | Precision before → after | Recall before → after | F1 before → after | Mean seconds before → after |
|---|---:|---:|---:|---:|---:|
| English | 3 → 3 | 50.0% → 100% | 50.0% → 100% | 50.0% → 100% | 32.25 → 26.61 |
| Arabic | 1 → 2 | 0% → 100% | Not evaluated → 100% | 0% → 100% | 28.40 → 31.13 |

## Interpretation review

These prose assessments are separate from the label and citation scores.

| Case | Baseline | Final | Interpretation notes |
|---|---|---|---|
| EN-01 bounded refund | Correct | Partially correct | Both runs classify it as routine. The final English explains the receipts condition, while the Arabic paraphrase is awkward and omits the distinction from ordinary wear. |
| EN-13 competing notice periods | Partially correct | Correct | Both explanations identify 21 and 42 days and the same exit trigger. The final review labels the conflict as a concern and cites both clauses. |
| EN-19 unannounced inspections | Partially correct | Partially correct | Correct risk and English meaning in both runs. The Arabic renderings use confusing wording for landlord and inspection. |
| AR-02 bounded refund | Incorrect | Partially correct | The routine label is corrected. The Arabic meaning remains clear. The final English should say outstanding rent to avoid implying that a history of any late payment defeats the refund. |
| AR-07 duplicate cleaning fee | Not evaluated | Not evaluated | The baseline provider request failed. The final review fell back with unverifiable output. A diagnostic trial generated the wrong fee amount and currency even though the cited text was real. |
| AR-13 competing notice periods | Not evaluated | Correct | The final output identifies the two notice periods, cites both clauses, and explains the inconsistency. There is a formatting error in one inline English clause ID, while the displayed evidence IDs are valid. |

The first prompt-only trial regressed on the pilot and was discarded. The retained
changes give the model more explicit bilingual examples and apply conservative
document-backed checks. An exact quote is still only a provenance check. The
monetary guard checks recognized explicit amounts and currencies in explanations,
and cannot validate every quantity or inferred contractual meaning.

The final prompt is longer than the baseline. The output cap is lower, and the
overall pilot mean fell about 1.45 seconds while the Arabic mean rose. These
single-run timings include model warmup and fallbacks. Long portfolio documents,
full-corpus inference, broad Arabic translation quality, and performance at scale
remain **Not evaluated**. No benchmark text was used as a prompt example.

## Browser holdout

The visible English upload identified a notice conflict across two PDF pages.
The Arabic heater-repair PDF exposed a separate label issue. Both the baseline
and the revised model described the conflict and cited both pages, yet returned
the maintenance category. The final label check recognizes that explicit
bilingual conflict label only when there are two verified source clauses.
Replaying all five stored live pilot outputs through the final label check
left their findings and measured scores identical. No repeat model inference
was used for that replay.

The final visible Brave retest returned a live Arabic contradiction labeled
`concern` with exact quotes from pages 1 and 2. Its Arabic wording still needs
review for fluency. Language switching, file removal, bilingual mobile layout,
reset and the calculator passed. Native Windows clicks, keyboard sample
selection and the Arabic PDF file picker passed separately. The backend suite
passed all 116 tests, and the Vite production build passed.
