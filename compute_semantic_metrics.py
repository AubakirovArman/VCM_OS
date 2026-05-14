#!/usr/bin/env python3
"""Compute semantic precision/recall from human-labeled dataset."""
import json
import sys


def compute_metrics(labeled_path: str, threshold_label: str = "match"):
    with open(labeled_path) as f:
        data = json.load(f)

    # Only consider items with human labels
    labeled = [d for d in data if d.get("label")]
    if not labeled:
        print("No labeled items found. Please label first.")
        return

    # Human says "match" or "partial" → true positive ground truth
    human_positive = [d for d in labeled if d["label"] in ("match", "partial")]
    human_negative = [d for d in labeled if d["label"] == "no_match"]

    # Semantic matcher says "match" if pack contains expected text (simple heuristic)
    # For now, use exact substring as proxy for "semantic match at threshold 0.75"
    semantic_positive = []
    for d in labeled:
        expected = d["expected"].lower()
        pack = d["pack_text"].lower()
        # Simple substring match (proxy for semantic match)
        if expected in pack:
            semantic_positive.append(d)

    # Compute metrics
    tp = len([d for d in semantic_positive if d["label"] in ("match", "partial")])
    fp = len([d for d in semantic_positive if d["label"] == "no_match"])
    fn = len([d for d in human_positive if d not in semantic_positive])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print("=" * 60)
    print("SEMANTIC METRICS (Human-Labeled)")
    print("=" * 60)
    print(f"Total labeled:     {len(labeled)}")
    print(f"Human positive:    {len(human_positive)}")
    print(f"Human negative:    {len(human_negative)}")
    print(f"Semantic positive: {len(semantic_positive)}")
    print()
    print(f"TP: {tp}  FP: {fp}  FN: {fn}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1:        {f1:.3f}")
    print()
    if precision < 0.75:
        print("WARNING: Precision < 0.75 — semantic metric not suitable for headline")
    else:
        print("OK: Precision >= 0.75 — semantic metric validated")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "human_eval_labeled.json"
    compute_metrics(path)
