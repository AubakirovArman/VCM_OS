"""F03 debug trace: compare vector vs sparse vs hybrid retrieval per scenario."""

import json
import tempfile
from typing import Dict, List, Set, Tuple

from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.scenarios.synthetic_projects import load_all_scenarios
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import MemoryObject, MemoryRequest
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex


def _find_gold_memories(store, scenario) -> Set[str]:
    """Find memory IDs that contain expected goals/decisions/errors."""
    gold_ids = set()
    all_mems = store.get_memories(project_id=scenario.project_id, limit=1000)
    for mem in all_mems:
        text = (mem.raw_text or "").lower()
        text += " " + (mem.compressed_summary or "").lower()
        for g in scenario.expected_goals:
            if g.lower() in text:
                gold_ids.add(mem.memory_id)
        for d in scenario.expected_decisions:
            if d.lower() in text:
                gold_ids.add(mem.memory_id)
        for e in scenario.expected_errors:
            if e.lower() in text:
                gold_ids.add(mem.memory_id)
    return gold_ids


def _recall_at_k(retrieved_ids: List[str], gold_ids: Set[str], k: int) -> float:
    if not gold_ids:
        return 1.0
    retrieved_set = set(retrieved_ids[:k])
    hits = len(retrieved_set & gold_ids)
    return hits / len(gold_ids)


def _mrr(retrieved_ids: List[str], gold_ids: Set[str]) -> float:
    if not gold_ids:
        return 1.0
    for rank, mid in enumerate(retrieved_ids):
        if mid in gold_ids:
            return 1.0 / (rank + 1)
    return 0.0


def _pack_inclusion_rate(pack, gold_ids: Set[str]) -> float:
    if not gold_ids:
        return 1.0
    included = set()
    for sec in pack.sections:
        for mid in sec.memory_ids:
            if mid in gold_ids:
                included.add(mid)
    return len(included) / len(gold_ids)


def run_f03_debug():
    scenarios = load_all_scenarios()
    normal = [s for s in scenarios if not s.name.startswith("h03_") and s.name != "false_memory_s05"]

    results = []
    for sc in normal[:5]:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/eval.db"
            store = SQLiteStore(db_path=db_path)
            vector_index = VectorIndex()
            sparse_index = SparseIndex()
            writer = MemoryWriter(store, vector_index, sparse_index)
            runner = ExperimentRunner(store, vector_index, sparse_index, writer)
            runner.ingest_scenario(sc)

            gold_ids = _find_gold_memories(store, sc)

            # Vector only
            vec_results = vector_index.search(sc.test_query, top_k=20)
            vec_ids = [mid for mid, _ in vec_results if store.get_memory(mid)]
            vec_ids_scoped = [mid for mid in vec_ids if store.get_memory(mid).project_id == sc.project_id]

            # Sparse only
            sparse_results = sparse_index.search(sc.test_query, top_k=20)
            sparse_ids = [mid for mid, _ in sparse_results if store.get_memory(mid)]
            sparse_ids_scoped = [mid for mid in sparse_ids if store.get_memory(mid).project_id == sc.project_id]

            # Hybrid (full VCM retrieval)
            request = MemoryRequest(
                project_id=sc.project_id,
                query=sc.test_query,
                task_type="general",
            )
            from vcm_os.schemas import RetrievalPlan
            plan = RetrievalPlan(
                needs_session=False,
                needs_project=True,
                needs_decisions=True,
                needs_errors=True,
                needs_code=True,
                needs_graph=False,
            )
            hybrid_memories = runner.reader.retrieve(request, plan)
            hybrid_ids = [m.memory_id for m in hybrid_memories[:20]]

            # Pack builder
            pack = runner.pack_builder.build(request, hybrid_memories[:50])

            # Build report
            report = {
                "scenario": sc.name,
                "query": sc.test_query,
                "gold_count": len(gold_ids),
                "vector_recall@5": _recall_at_k(vec_ids_scoped, gold_ids, 5),
                "vector_recall@10": _recall_at_k(vec_ids_scoped, gold_ids, 10),
                "vector_recall@20": _recall_at_k(vec_ids_scoped, gold_ids, 20),
                "vector_mrr": _mrr(vec_ids_scoped, gold_ids),
                "sparse_recall@5": _recall_at_k(sparse_ids_scoped, gold_ids, 5),
                "sparse_recall@10": _recall_at_k(sparse_ids_scoped, gold_ids, 10),
                "sparse_recall@20": _recall_at_k(sparse_ids_scoped, gold_ids, 20),
                "sparse_mrr": _mrr(sparse_ids_scoped, gold_ids),
                "hybrid_recall@5": _recall_at_k(hybrid_ids, gold_ids, 5),
                "hybrid_recall@10": _recall_at_k(hybrid_ids, gold_ids, 10),
                "hybrid_recall@20": _recall_at_k(hybrid_ids, gold_ids, 20),
                "hybrid_mrr": _mrr(hybrid_ids, gold_ids),
                "pack_inclusion_rate": _pack_inclusion_rate(pack, gold_ids),
                "pack_tokens": pack.token_estimate,
                "sparse_unique": len(set(sparse_ids_scoped) - set(vec_ids_scoped)),
                "vector_unique": len(set(vec_ids_scoped) - set(sparse_ids_scoped)),
            }
            results.append(report)

            # Print per-scenario details
            print(f"\n{'='*60}")
            print(f"Scenario: {sc.name}")
            print(f"Query: {sc.test_query}")
            print(f"Gold memories: {len(gold_ids)}")
            print(f"\nRetriever Performance:")
            print(f"  Vector  recall@5={report['vector_recall@5']:.2f} @10={report['vector_recall@10']:.2f} @20={report['vector_recall@20']:.2f} MRR={report['vector_mrr']:.3f}")
            print(f"  Sparse  recall@5={report['sparse_recall@5']:.2f} @10={report['sparse_recall@10']:.2f} @20={report['sparse_recall@20']:.2f} MRR={report['sparse_mrr']:.3f}")
            print(f"  Hybrid  recall@5={report['hybrid_recall@5']:.2f} @10={report['hybrid_recall@10']:.2f} @20={report['hybrid_recall@20']:.2f} MRR={report['hybrid_mrr']:.3f}")
            print(f"\nSparse unique IDs: {report['sparse_unique']} | Vector unique IDs: {report['vector_unique']}")
            print(f"Pack inclusion rate: {report['pack_inclusion_rate']:.2f} | Pack tokens: {report['pack_tokens']}")

            if gold_ids:
                print(f"\nGold IDs: {list(gold_ids)[:5]}")
                print(f"Vector top-5: {vec_ids_scoped[:5]}")
                print(f"Sparse top-5: {sparse_ids_scoped[:5]}")
                print(f"Hybrid top-5: {hybrid_ids[:5]}")

    # Aggregate
    print(f"\n{'='*60}")
    print("AGGREGATE")
    print(f"{'='*60}")
    for metric in ["vector_recall@5", "vector_recall@10", "sparse_recall@5", "sparse_recall@10",
                   "hybrid_recall@5", "hybrid_recall@10", "vector_mrr", "sparse_mrr", "hybrid_mrr",
                   "pack_inclusion_rate", "sparse_unique", "vector_unique"]:
        vals = [r[metric] for r in results]
        avg = sum(vals) / len(vals)
        print(f"  {metric:25s}: avg={avg:.3f}")

    with open("f03_debug.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to f03_debug.json")


if __name__ == "__main__":
    run_f03_debug()
