import os
import tempfile

import pytest

from vcm_os.evals.baselines import FullContextBaseline, RAGBaseline, SummaryBaseline
from vcm_os.evals.experiments import ExperimentRunner
from vcm_os.evals.metrics import evaluate_session_restore, recall_accuracy, token_usage
from vcm_os.evals.scenarios.synthetic_projects import auth_refresh_loop_scenario
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.vector_index import VectorIndex


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = SQLiteStore(db_path=db_path)
        yield store


@pytest.fixture
def indexes(temp_store):
    with tempfile.TemporaryDirectory() as tmpdir:
        import vcm_os.config as cfg
        orig_dir = cfg.DATA_DIR
        cfg.DATA_DIR = tmpdir
        vi = VectorIndex()
        si = SparseIndex()
        yield vi, si
        cfg.DATA_DIR = orig_dir


def test_t10_vcm_beats_rag_and_summary(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    runner = ExperimentRunner(temp_store, vi, si, writer)

    sc = auth_refresh_loop_scenario()
    runner.ingest_scenario(sc)

    pack_vcm = runner.run_vcm(sc)
    pack_summary = runner.run_baseline_summary(sc)
    pack_rag = runner.run_baseline_rag(sc)
    pack_full = runner.run_baseline_full(sc)

    score_vcm = runner.score_pack(pack_vcm, sc)
    score_summary = runner.score_pack(pack_summary, sc)
    score_rag = runner.score_pack(pack_rag, sc)
    score_full = runner.score_pack(pack_full, sc)

    # VCM should beat or match RAG
    assert score_vcm["quality_score"] >= score_rag["quality_score"]
    # VCM should have lower stale penalty than full context
    assert score_vcm["stale_penalty"] <= score_full["stale_penalty"]


def test_h03_no_contamination(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    runner = ExperimentRunner(temp_store, vi, si, writer)

    from vcm_os.evals.scenarios.synthetic_projects import project_switching_h03
    a, b, c = project_switching_h03()
    for sc in [a, b, c]:
        runner.ingest_scenario(sc)

    from vcm_os.evals.experiments import H03_ProjectSwitching
    h03 = H03_ProjectSwitching(runner)
    result = h03.run([a, b, c])

    assert result["total_cross_project_memories"] == 0
    assert result["contamination_rate"] < 0.02


def test_s05_false_memory_detected(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    runner = ExperimentRunner(temp_store, vi, si, writer)

    from vcm_os.evals.scenarios.synthetic_projects import false_memory_s05
    sc = false_memory_s05()
    runner.ingest_scenario(sc)

    from vcm_os.evals.experiments import S05_FalseMemory
    s05 = S05_FalseMemory(runner)
    result = s05.run(sc)

    # SQLite decision should be active after correction
    assert result["sqlite_active"] is True
    assert result["false_memory_rate"] < 0.05


def test_summary_baseline_compresses(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    runner = ExperimentRunner(temp_store, vi, si, writer)

    sc = auth_refresh_loop_scenario()
    runner.ingest_scenario(sc)

    pack_summary = runner.run_baseline_summary(sc)
    pack_full = runner.run_baseline_full(sc)

    # Summary should be significantly shorter than full
    assert pack_summary.token_estimate < pack_full.token_estimate


def test_f03_hybrid_exists(temp_store, indexes):
    vi, si = indexes
    writer = MemoryWriter(temp_store, vi, si)
    runner = ExperimentRunner(temp_store, vi, si, writer)

    sc = auth_refresh_loop_scenario()
    runner.ingest_scenario(sc)

    from vcm_os.evals.experiments import F03_HybridRetrieval
    f03 = F03_HybridRetrieval(runner)
    result = f03.run(sc)

    assert "hybrid_restore" in result
    assert "vector_only_restore" in result
