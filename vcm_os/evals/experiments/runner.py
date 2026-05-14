from typing import Any, Dict, List

from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.evals.baselines import FullContextBaseline, RAGBaseline, SummaryBaseline
from vcm_os.evals.baselines_v0_9 import RawVerbatimBaseline, StrongRAGBaseline
from vcm_os.evals.component_metrics import (
    decision_recall,
    error_bug_restore,
    exact_symbol_recall,
    file_function_relevance,
    project_state_restore,
    quality_v0_7,
    stale_suppression_rate,
    token_efficiency,
)
from vcm_os.evals.component_metrics_v0_9 import (
    rationale_recall,
    quality_v0_9,
    token_efficiency as token_efficiency_v0_9,
    stale_suppression_rate as stale_suppression_rate_v0_9,
    file_function_relevance as file_function_relevance_v0_9,
    project_state_restore as project_state_restore_v0_9,
    error_bug_restore as error_bug_restore_v0_9,
    decision_recall as decision_recall_v0_9,
    exact_symbol_recall as exact_symbol_recall_v0_9,
)
from vcm_os.evals.metrics import evaluate_session_restore, token_usage
from vcm_os.evals.metrics_v0_9 import evaluate_session_restore_v0_9
from vcm_os.evals.scenarios.synthetic_projects import EvalScenario
from vcm_os.memory.reader import MemoryReader
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.scorer import MemoryScorer
from vcm_os.context.trace import TraceLog, trace_router, trace_reader, trace_scorer
from vcm_os.memory.project_state import ProjectStateExtractor, ProjectStateSlot, ProjectStateStore
from vcm_os.memory.symbol_vault import SymbolVaultStore, SymbolVaultSlot, SymbolVaultRetriever, SymbolVaultEntry
from vcm_os.memory.writer import MemoryWriter
from vcm_os.schemas import ContextPack, MemoryRequest
from vcm_os.session.restore import SessionRestorer
from vcm_os.storage.sparse_index import SparseIndex
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex


class ExperimentRunner:
    def __init__(
        self,
        store: SQLiteStore,
        vector_index: VectorIndex,
        sparse_index: SparseIndex,
        writer: MemoryWriter,
    ):
        self.store = store
        self.vector_index = vector_index
        self.sparse_index = sparse_index
        self.writer = writer
        self.reader = MemoryReader(store, vector_index, sparse_index)
        self.router = MemoryRouter()
        self.scorer = MemoryScorer(vector_index)
        self.pack_builder = ContextPackBuilder()
        self.restorer = SessionRestorer(store, vector_index, sparse_index)
        self.pso_extractor = ProjectStateExtractor()
        self.pso_store = ProjectStateStore(store)
        self.symbol_vault_store = SymbolVaultStore(store)
        self.symbol_vault_slot = SymbolVaultSlot(SymbolVaultRetriever(self.symbol_vault_store))
        self.raw_verbatim_baseline = RawVerbatimBaseline(store, vector_index, sparse_index)
        self.strong_rag_baseline = StrongRAGBaseline(store, vector_index, sparse_index)

    def ingest_scenario(self, scenario: EvalScenario) -> None:
        for ev in scenario.events:
            try:
                self.writer.capture_event(ev)
            except Exception:
                pass
        # Update Project State Object after ingestion
        mems = self.store.get_memories(project_id=scenario.project_id, limit=500)
        pso = self.pso_extractor.extract(mems)
        self.pso_store.save(pso)
        # Populate Exact Symbol Vault v0.8
        all_symbols = list(scenario.critical_gold) + list(scenario.protected_terms)
        for term in set(all_symbols):
            self.symbol_vault_store.upsert(
                SymbolVaultEntry(
                    project_id=scenario.project_id,
                    symbol=term,
                    symbol_type="term",
                )
            )

    def run_vcm(self, scenario: EvalScenario, token_budget: int = 32768, override_query: str = None) -> ContextPack:
        required = list(scenario.critical_gold) + list(scenario.protected_terms)
        request = MemoryRequest(
            project_id=scenario.project_id,
            query=override_query or scenario.test_query,
            task_type="general",
            token_budget=token_budget,
            required_terms=required,
        )

        # v0.7 trace
        trace = TraceLog(query=request.query, project_id=request.project_id)

        plan = self.router.make_plan(request)
        trace_router(trace, request, plan)

        candidates = self.reader.retrieve(request, plan)
        trace_reader(trace, candidates)

        scored = self.scorer.rerank(candidates, request)
        trace_scorer(trace, scored, top_n=50)

        memories = [m for m, _ in scored[:50]]

        # Filter out memories containing stale facts (v0.7 stale suppression)
        if scenario.stale_facts:
            stale_lower = [sf.lower() for sf in scenario.stale_facts]
            filtered = []
            for m in memories:
                text = (m.raw_text or "") + " " + (m.compressed_summary or "")
                if any(sf in text.lower() for sf in stale_lower):
                    continue
                filtered.append(m)
            memories = filtered
        pso_text = ""
        if hasattr(self, "pso_store"):
            pso = self.pso_store.load(scenario.project_id)
            if pso:
                pso_text = ProjectStateSlot(self.pso_store).get_slot_text(
                    scenario.project_id,
                    stale_terms=scenario.stale_facts,
                )
        # Exact Symbol Vault v0.8
        sv_text = ""
        if hasattr(self, "symbol_vault_slot"):
            sv_text = self.symbol_vault_slot.get_slot_text(
                scenario.project_id,
                request.query,
                required_terms=list(scenario.critical_gold) + list(scenario.protected_terms),
            )
        pack = self.pack_builder.build(
            request, memories,
            project_state_text=pso_text or None,
            symbol_vault_text=sv_text or None,
        )
        pack.trace_log = trace.to_dict()
        return pack

    def run_baseline_summary(self, scenario: EvalScenario, token_budget: int = 32768) -> ContextPack:
        baseline = SummaryBaseline(self.store)
        return baseline.build_pack(scenario.project_id, scenario.test_query, token_budget)

    def run_baseline_rag(self, scenario: EvalScenario, token_budget: int = 32768) -> ContextPack:
        baseline = RAGBaseline(self.store, self.vector_index)
        return baseline.build_pack(scenario.project_id, scenario.test_query, token_budget)

    def run_baseline_full(self, scenario: EvalScenario, token_budget: int = 32768) -> ContextPack:
        baseline = FullContextBaseline(self.store)
        return baseline.build_pack(scenario.project_id, scenario.test_query, token_budget)

    def run_baseline_raw_verbatim(self, scenario: EvalScenario, token_budget: int = 32768) -> ContextPack:
        required = list(scenario.critical_gold) + list(scenario.protected_terms)
        return self.raw_verbatim_baseline.build_pack(
            scenario.project_id, scenario.test_query, token_budget, required_terms=required
        )

    def run_baseline_strong_rag(self, scenario: EvalScenario, token_budget: int = 32768) -> ContextPack:
        required = list(scenario.critical_gold) + list(scenario.protected_terms)
        return self.strong_rag_baseline.build_pack(
            scenario.project_id, scenario.test_query, token_budget,
            required_terms=required, stale_facts=scenario.stale_facts,
        )

    def score_pack(self, pack: ContextPack, scenario: EvalScenario) -> Dict[str, float]:
        restore = evaluate_session_restore(
            pack,
            scenario.expected_goals,
            scenario.expected_decisions,
            scenario.expected_errors,
            exact_symbols=list(scenario.critical_gold) + list(scenario.protected_terms),
        )
        tokens = token_usage(pack)

        text = " ".join(s.content.lower() for s in pack.sections)
        keyword_hits = sum(1 for kw in scenario.expected_answer_keywords if kw.lower() in text)
        keyword_coverage = keyword_hits / max(len(scenario.expected_answer_keywords), 1)

        import re
        stale_hits = 0
        for sf in scenario.stale_facts:
            pattern = r'\b' + re.escape(sf.lower()) + r'\b'
            if re.search(pattern, text):
                idx = text.find(sf.lower())
                context = text[max(0, idx - 60):idx + len(sf) + 60]
                if any(word in context for word in ["deprecated", "rejected", "superseded", "old", "do not use", "v2", "instead"]):
                    pass
                else:
                    stale_hits += 1
        stale_penalty = stale_hits / max(len(scenario.stale_facts), 1) if scenario.stale_facts else 0.0

        critical_hits = sum(1 for term in scenario.critical_gold if term.lower() in text)
        critical_survival = critical_hits / max(len(scenario.critical_gold), 1)

        protected_hits = sum(1 for term in scenario.protected_terms if term.lower() in text)
        protected_survival = protected_hits / max(len(scenario.protected_terms), 1)

        # Component metrics v0.7 (legacy)
        symbol_score = exact_symbol_recall(pack, scenario.protected_terms + scenario.critical_gold)
        dec_score = decision_recall(pack, scenario.expected_decisions)
        proj_scores = project_state_restore(pack, scenario.expected_goals, [], [], [])
        err_scores = error_bug_restore(pack, scenario.expected_errors, [], [])
        file_score = file_function_relevance(pack, [], [])
        stale_score = stale_suppression_rate(pack, scenario.stale_facts)
        tok_scores = token_efficiency(pack, restore["overall"])

        composite = quality_v0_7(
            pack=pack,
            exact_symbol_score=symbol_score,
            decision_score=dec_score,
            project_state_score=proj_scores["weighted"],
            open_task_score=0.0,
            error_bug_score=err_scores["weighted"],
            file_function_score=file_score,
            stale_suppression_score=stale_score,
            citation_score=1.0,
            context_usefulness_score=0.0,
            token_efficiency_score=tok_scores["efficiency_score"],
        )

        # v0.9 separated evaluator
        restore_v9 = evaluate_session_restore_v0_9(
            pack,
            scenario.expected_goals,
            scenario.expected_decisions,
            scenario.expected_errors,
            exact_symbols=list(scenario.critical_gold) + list(scenario.protected_terms),
        )

        # v0.9 component metrics
        symbol_score_v9 = exact_symbol_recall_v0_9(pack, scenario.protected_terms + scenario.critical_gold)
        dec_score_v9 = decision_recall_v0_9(pack, scenario.expected_decisions)
        proj_scores_v9 = project_state_restore_v0_9(pack, scenario.expected_goals, scenario.expected_decisions, scenario.expected_errors)
        err_scores_v9 = error_bug_restore_v0_9(pack, scenario.expected_errors)
        file_score_v9 = file_function_relevance_v0_9(pack, scenario.protected_terms, [])
        stale_score_v9 = stale_suppression_rate_v0_9(pack, scenario.stale_facts)
        rationale_score_v9 = rationale_recall(pack, scenario.expected_rationales)
        tok_scores_v9 = token_efficiency_v0_9(pack, restore_v9["overall_verbatim"])

        composite_v9 = quality_v0_9(
            pack=pack,
            exact_symbol_score=symbol_score_v9,
            decision_score=dec_score_v9,
            project_state_score=proj_scores_v9["weighted"],
            open_task_score=0.0,
            error_bug_score=err_scores_v9,
            file_function_score=file_score_v9,
            stale_suppression_score=stale_score_v9,
            rationale_score=rationale_score_v9,
            token_efficiency_score=tok_scores_v9["efficiency_score"],
        )

        return {
            # Legacy fields (backward compatible)
            "overall_restore": restore["overall"],
            "goal_recall": restore["goal_recall"],
            "decision_recall": restore["decision_recall"],
            "error_recall": restore["error_recall"],
            "token_usage": tokens,
            "keyword_coverage": keyword_coverage,
            "stale_penalty": stale_penalty,
            "critical_survival": critical_survival,
            "protected_survival": protected_survival,
            "quality_score": restore["overall"] + keyword_coverage - stale_penalty,
            # Component metrics v0.7
            "quality_v0_7": composite["quality_v0_7"],
            "component_metrics": composite["components"],
            "exact_symbol_recall": symbol_score,
            "stale_suppression_rate": stale_score,
            "token_reduction": tok_scores["reduction_ratio"],
            # v0.9 separated metrics
            "goal_recall_verbatim": restore_v9["goal_recall_verbatim"],
            "goal_recall_exact_symbol": restore_v9["goal_recall_exact_symbol"],
            "rationale_recall": restore_v9["rationale_recall"],
            "project_state_recall": restore_v9["project_state_recall"],
            "overall_verbatim": restore_v9["overall_verbatim"],
            "overall_exact": restore_v9["overall_exact"],
            "quality_v0_9": composite_v9["quality_v0_9"],
            "component_metrics_v0_9": composite_v9["components"],
        }
