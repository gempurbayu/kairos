"""Compare a saved candidate plan with human-marked moments; no media upload."""
import argparse
import json
import math
from pathlib import Path


def interval(value):
    start, end = float(value["start"]), float(value["end"])
    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
        raise ValueError("Intervals require finite timestamps with 0 <= start < end")
    return start, end


def evaluate(plan, annotations, top_n=5, threshold=.3):
    if not 1 <= top_n <= 20 or not 0 < threshold <= 1:
        raise ValueError("Use top_n 1–20 and overlap threshold in (0, 1]")
    expected = [interval(item) for item in annotations["moments"]]
    if not expected:
        raise ValueError("Mark at least one expected moment")
    if plan.get("source_sha256") != annotations.get("source_sha256") or not plan.get("source_sha256"):
        raise ValueError("Annotations and candidate plan must refer to the same source hash")
    proposed = sorted(plan["clips"], key=lambda c: c["score"], reverse=True)[:top_n]
    matches = set()
    rows = []
    relevant = 0
    for item in proposed:
        start, end = interval(item)
        overlaps = [max(0, min(end, b) - max(start, a)) / (max(end, b) - min(start, a)) for a, b in expected]
        hits = [i for i, score in enumerate(overlaps) if score >= threshold]
        matches.update(hits)
        relevant += bool(hits)
        rows.append({"id": item["id"], "matched_moments": hits, "best_iou": round(max(overlaps), 3)})
    return {"top_n": top_n, "returned": len(proposed), "iou_threshold": threshold,
            "precision": relevant / len(proposed) if proposed else 0,
            "moment_recall": len(matches) / len(expected),
            "missed_moments": [i for i in range(len(expected)) if i not in matches],
            "candidates": rows,
            "note": "Interval overlap only. Human review must assess context, framing, captions, and relevance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("annotations")
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()
    report = evaluate(json.loads(Path(args.plan).read_text()), json.loads(Path(args.annotations).read_text()), args.top_n)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
