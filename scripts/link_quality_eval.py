#!/usr/bin/env python3
"""Link quality evaluation — measure precision and recall of auto-linked memories.

Heuristic evaluation (no human gold labels):
- Precision: of all linked pairs, how many share at least 2 signals (file/session/keyword/temporal)
- Recall: of all memory pairs that share a session or 2+ files, how many are linked
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcm_os.storage.sqlite_store import SQLiteStore


def _keywords(text: str) -> set:
    if not text:
        return set()
    stopwords = {"the","a","an","is","are","was","were","be","been","being","have","has","had","do","does","did","will","would","could","should","may","might","must","shall","can","need","to","of","in","for","on","with","at","by","from","as","into","through","during","before","after","above","below","between","under","and","but","or","yet","so","if","because","although","though","while","where","when","that","which","who","whom","whose","what","this","these","those","i","me","my","we","us","our","you","your","he","him","his","she","her","it","its","they","them","their"}
    words = set(w.lower() for w in text.split() if len(w) > 3 and w.lower() not in stopwords)
    return words


def evaluate_links(store: SQLiteStore):
    with store._conn() as conn:
        # Load all memories
        mem_rows = conn.execute(
            "SELECT memory_id, project_id, session_id, raw_text, timestamp FROM memory_objects"
        ).fetchall()
        memories = {r[0]: {
            "id": r[0], "project_id": r[1], "session_id": r[2],
            "raw_text": r[3] or "", "timestamp": r[4],
            "keywords": _keywords(r[3] or ""),
        } for r in mem_rows}

        # Load file references (JSON column in memory_objects)
        import json
        file_rows = conn.execute("SELECT memory_id, file_references FROM memory_objects WHERE file_references IS NOT NULL AND file_references != ''").fetchall()
        mem_files = defaultdict(set)
        for mid, fref_json in file_rows:
            try:
                refs = json.loads(fref_json)
                if isinstance(refs, list):
                    mem_files[mid].update(str(r) for r in refs if r)
            except Exception:
                pass

        # Load links
        link_rows = conn.execute(
            "SELECT source_id, target_id, relation_type, confidence FROM memory_links"
        ).fetchall()
        links = [(r[0], r[1], r[2], r[3]) for r in link_rows]

    if not links:
        print("No links found.")
        return

    # Precision: linked pairs with at least 2 shared signals
    good_links = 0
    link_details = []
    for src, tgt, rel, conf in links:
        m1 = memories.get(src, {})
        m2 = memories.get(tgt, {})
        signals = 0
        reasons = []
        if m1.get("session_id") and m1["session_id"] == m2.get("session_id"):
            signals += 1
            reasons.append("same_session")
        shared_files = mem_files.get(src, set()) & mem_files.get(tgt, set())
        if shared_files:
            signals += 1
            reasons.append("shared_files")
        shared_kw = m1.get("keywords", set()) & m2.get("keywords", set())
        if len(shared_kw) >= 2:
            signals += 1
            reasons.append("keywords")
        if m1.get("timestamp") and m2.get("timestamp"):
            signals += 1
            reasons.append("temporal")

        is_good = signals >= 2
        if is_good:
            good_links += 1
        link_details.append({
            "source": src[:8], "target": tgt[:8], "relationship": rel,
            "confidence": conf, "signals": signals, "good": is_good,
            "reasons": reasons,
        })

    precision = good_links / len(links) if links else 0

    # Recall heuristic: count pairs that share session or 2+ files
    should_be_linked = 0
    actually_linked = 0
    mem_list = list(memories.values())
    linked_set = set()
    for src, tgt, _, _ in links:
        linked_set.add(tuple(sorted((src, tgt))))

    for i, m1 in enumerate(mem_list):
        for m2 in mem_list[i+1:]:
            if m1["project_id"] != m2["project_id"]:
                continue
            has_signal = False
            if m1["session_id"] and m1["session_id"] == m2["session_id"]:
                has_signal = True
            shared_files = mem_files.get(m1["id"], set()) & mem_files.get(m2["id"], set())
            if len(shared_files) >= 2:
                has_signal = True
            if not has_signal:
                continue
            should_be_linked += 1
            if tuple(sorted((m1["id"], m2["id"]))) in linked_set:
                actually_linked += 1

    recall = actually_linked / should_be_linked if should_be_linked else 0

    print("=" * 60)
    print("Link Quality Evaluation")
    print("=" * 60)
    print(f"Total memories: {len(memories)}")
    print(f"Total links: {len(links)}")
    print(f"Good links (≥2 signals): {good_links}")
    print(f"Precision: {precision:.3f}")
    print(f"Should-be-linked pairs: {should_be_linked}")
    print(f"Actually linked: {actually_linked}")
    print(f"Recall: {recall:.3f}")

    # Breakdown by relationship type
    by_rel = defaultdict(lambda: {"total": 0, "good": 0})
    for d in link_details:
        by_rel[d["relationship"]]["total"] += 1
        if d["good"]:
            by_rel[d["relationship"]]["good"] += 1

    print("\nBy relationship type:")
    for rel, counts in sorted(by_rel.items()):
        p = counts["good"] / counts["total"] if counts["total"] else 0
        print(f"  {rel:20s}  good={counts['good']}/{counts['total']}  precision={p:.3f}")

    result = {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "total_links": len(links),
        "good_links": good_links,
        "should_be_linked": should_be_linked,
        "actually_linked": actually_linked,
        "by_relationship": {rel: dict(counts) for rel, counts in by_rel.items()},
    }
    with open("link_quality_results.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nSaved to link_quality_results.json")


def main():
    store = SQLiteStore()
    evaluate_links(store)


if __name__ == "__main__":
    main()
