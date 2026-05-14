#!/usr/bin/env python3
"""Human evaluation dataset for semantic threshold validation.

Generates goal/pack pairs from holdout scenarios for human annotation.
After manual annotation, computes precision/recall for threshold 0.75.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.holdout_scenarios import load_holdout_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.evals.semantic_matcher import SemanticGoalMatcher


def generate_human_eval_dataset():
    store = SQLiteStore()
    vi = VectorIndex()
    si = SparseIndex()
    writer = MemoryWriter(store, vi, si)
    runner = ExperimentRunner(store, vi, si, writer)

    holdout = load_holdout_scenarios()
    pairs = []

    for sc in holdout:
        runner.ingest_scenario(sc)
        pack = runner.run_vcm(sc)

        for goal in sc.expected_goals:
            # Check all three tiers
            pack_text = " ".join(s.content for s in pack.sections).lower()
            verbatim = goal.lower() in pack_text
            semantic = evaluate_semantic_restore(
                pack, [goal], [], [], threshold=0.75
            )
            semantic_score = semantic["semantic_goal"]

            pairs.append({
                "scenario": sc.name,
                "goal": goal,
                "pack_preview": pack_text[:300],
                "verbatim": verbatim,
                "semantic_score": float(semantic_score),
                "semantic_match": semantic_score >= 0.75,
                "human_label": None,  # To be filled manually
            })

    with open("human_eval_dataset.json", "w") as f:
        json.dump(pairs, f, indent=2)

    print(f"Generated {len(pairs)} goal/pack pairs for human annotation")
    print("File: human_eval_dataset.json")
    print("\nAnnotation instructions:")
    print("  match     — goal meaning fully captured in pack")
    print("  partial   — some aspects captured but incomplete")
    print("  no_match  — goal meaning not present in pack")
    return pairs


def compute_metrics(human_labels, semantic_matches):
    """Compute precision/recall for semantic threshold."""
    tp = sum(1 for h, s in zip(human_labels, semantic_matches) if h == "match" and s)
    fp = sum(1 for h, s in zip(human_labels, semantic_matches) if h != "match" and s)
    fn = sum(1 for h, s in zip(human_labels, semantic_matches) if h == "match" and not s)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def auto_annotate_and_evaluate():
    """Auto-annotate using simple heuristics, then compute metrics."""
    store = SQLiteStore()
    vi = VectorIndex()
    si = SparseIndex()
    writer = MemoryWriter(store, vi, si)
    runner = ExperimentRunner(store, vi, si, writer)

    holdout = load_holdout_scenarios()
    human_labels = []
    semantic_matches = []

    for sc in holdout:
        runner.ingest_scenario(sc)
        pack = runner.run_vcm(sc)
        pack_text = " ".join(s.content for s in pack.sections).lower()

        for goal in sc.expected_goals:
            matcher = SemanticGoalMatcher(vi, threshold=0.75)
            semantic = matcher.match_goals(pack, [goal])
            semantic_match = semantic["semantic_goal_recall"] >= 0.75
            semantic_matches.append(semantic_match)

            # Auto-annotate: exact substring → match, partial words → partial, else → no_match
            goal_lower = goal.lower()
            words = [w for w in goal_lower.split() if len(w) > 3]
            matches = sum(1 for w in words if w in pack_text)

            if goal_lower in pack_text:
                human_labels.append("match")
            elif matches >= len(words) * 0.5:
                human_labels.append("partial")
            else:
                human_labels.append("no_match")

    metrics = compute_metrics(human_labels, semantic_matches)

    print("=" * 60)
    print("HUMAN EVALUATION (Auto-annotated)")
    print("=" * 60)
    print(f"Total pairs: {len(human_labels)}")
    print(f"Human matches: {sum(1 for h in human_labels if h == 'match')}")
    print(f"Human partial: {sum(1 for h in human_labels if h == 'partial')}")
    print(f"Human no_match: {sum(1 for h in human_labels if h == 'no_match')}")
    print(f"\nSemantic threshold 0.75:")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall:    {metrics['recall']:.3f}")
    print(f"  F1:        {metrics['f1']:.3f}")
    print(f"  TP: {metrics['true_positives']}, FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}")

    # Also test thresholds 0.70, 0.75, 0.80
    print("\n--- Threshold comparison ---")
    for thresh in [0.70, 0.75, 0.80]:
        sem_matches = []
        for sc in holdout:
            runner.ingest_scenario(sc)
            pack = runner.run_vcm(sc)
            for goal in sc.expected_goals:
                matcher = SemanticGoalMatcher(vi, threshold=thresh)
                semantic = matcher.match_goals(pack, [goal])
                sem_matches.append(semantic["semantic_goal_recall"] >= thresh)
        m = compute_metrics(human_labels, sem_matches)
        print(f"  {thresh}: P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")

    return metrics


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        generate_human_eval_dataset()
    else:
        auto_annotate_and_evaluate()
