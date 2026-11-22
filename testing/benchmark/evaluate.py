"""Measure live Ollama agreement with fixed labels through the existing text API."""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from time import perf_counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from app.main import app

# Fixed before the baseline. Covers ordinary terms, charges, access and direct conflicts.
PILOT = ("en-01", "en-13", "en-19", "ar-02", "ar-07", "ar-13")


def cases():
    return [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines()]


def score(case, result, seconds):
    live = result.get("analysis_method") == "ollama_chat"
    findings = result.get("findings", []) if live else []
    sources = {item["id"]: item for item in result.get("clauses", [])}
    quotes, valid = 0, 0
    predictions = []
    for finding in findings:
        ids = set()
        for evidence in finding.get("evidence", []):
            quotes += 1
            source = sources.get(evidence["clause_id"])
            if source and evidence["quote"] and evidence["quote"] in source["text"] and source["page"] == evidence["page"]:
                valid += 1
                ids.add(evidence["clause_id"])
        if finding.get("risk") != "routine" or finding["category"] == "contradiction":
            predictions.append((finding["category"], finding.get("risk"), ids))
    remaining = list(predictions)
    tp = 0
    for expected in case["expected"]:
        required = {item["clause_id"] for item in expected["evidence"]}
        for i, (category, risk, ids) in enumerate(remaining):
            if (category, risk) == (expected["category"], expected["risk"]) and required <= ids:
                remaining.pop(i)
                tp += 1
                break
    fp, fn = len(predictions) - tp, len(case["expected"]) - tp
    category_overlap = {p[0] for p in predictions} & {e["category"] for e in case["expected"]}
    if not live:
        status = "Not evaluated"
    elif case["ambiguous"]:
        status = "Uncertain"
    elif fp == fn == 0 and valid == quotes:
        status = "Correct"
    elif tp or category_overlap:
        status = "Partially correct"
    else:
        status = "Incorrect"
    return {"id": case["id"], "language": case["language"], "status": status,
            "seconds": round(seconds, 3), "live": live, "tp": tp, "fp": fp, "fn": fn,
            "expected_contradiction": case["contradiction"],
            "contradiction_match": any(p[0] == "contradiction" for p in predictions) == case["contradiction"],
            "valid_citations": valid, "citations": quotes, "findings": findings,
            "fallback": result.get("fallback_reason"), "omitted": result.get("omitted_findings", 0)}


def summarize(rows):
    measured = [row for row in rows if row["live"] and row["status"] != "Uncertain"]
    tp, fp, fn = (sum(row[key] for row in measured) for key in ("tp", "fp", "fn"))
    total = sum(row["citations"] for row in measured)

    def ratio(numerator, denominator):
        return round(numerator / denominator, 4) if denominator else None
    return {"attempted": len(rows), "scored": len(measured), "tp": tp, "fp": fp, "fn": fn,
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
            "contradiction_accuracy": ratio(sum(row["contradiction_match"] for row in measured), len(measured)),
            "citation_validity": ratio(sum(row["valid_citations"] for row in measured), total),
            "citations": total,
            "fallback_frequency": ratio(sum(not row["live"] for row in rows), len(rows)),
            "mean_seconds": round(mean(row["seconds"] for row in rows), 3) if rows else None,
            "statuses": dict(Counter(row["status"] for row in rows))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true")
    group.add_argument("--ids", nargs="+")
    args = parser.parse_args()
    selected = set(args.ids or PILOT)
    dataset = cases()
    if selected - {case["id"] for case in dataset}:
        parser.error("Unknown case ID")
    os.environ["AI_PROVIDER"] = "ollama"
    rows = []
    client = TestClient(app)
    for case in dataset:
        if not args.all and case["id"] not in selected:
            continue
        start = perf_counter()
        response = client.post(f'/api/analyze-text?lang={case["language"]}',
                               headers={"X-ClauseX-AI-Consent": "run-local"}, json={"text": case["text"]})
        response.raise_for_status()
        row = score(case, response.json(), perf_counter() - start)
        rows.append(row)
        print(case["id"], row["status"], row["seconds"], row["fallback"], flush=True)
        summary = {lang: summarize([r for r in rows if r["language"] == lang]) for lang in ("en", "ar")}
        summary["overall"] = summarize(rows)
        args.output.write_text(json.dumps({"model": os.environ.get("OLLAMA_MODEL") or "qwen3:4b",
                                          "summary": summary, "cases": rows}, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")


if __name__ == "__main__":
    main()
