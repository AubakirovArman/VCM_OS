#!/usr/bin/env python3
"""Dogfooding VCM-OS: real coding sessions on VCM-OS itself.

Simulates 5 real dev sessions, then measures restore quality.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcm_os.evals.experiments.runner import ExperimentRunner
from vcm_os.evals.scenarios.types import EvalScenario, _evt
from vcm_os.memory.writer import MemoryWriter
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex


def session_1_token_optimization() -> EvalScenario:
    """Real session: optimizing token usage in pack builder."""
    pid = "vcm_os_tokopt"
    sid = "sess_tokopt_001"
    events = [
        _evt(pid, sid, "user_message",
             "Goal: reduce VCM pack tokens from 83 to ≤60. Decision: cut filler sections (intents, reflections, procedures) for general tasks. Keep decisions/errors/code only."),
        _evt(pid, sid, "code_change",
             "Modified assembler.py: made goals/requirements/intents conditional, reduced max_items, lowered budgets.",
             {"file_path": "vcm_os/context/pack_builder/assembler.py"}),
        _evt(pid, sid, "error",
             "Tests failed: test_t10_vcm_beats_rag. VCM restore dropped to 0.17 on auth_refresh_loop.",
             {"error_kind": "test_failure"}),
        _evt(pid, sid, "user_message",
             "Fix: don't strip fluff from compressed text. Preserve verbatim matching. Keep per-item cap at 80 for protected terms."),
        _evt(pid, sid, "code_change",
             "Restored original compression in compact_assembler. Added adaptive cap: 100 for protected terms, 60 otherwise.",
             {"file_path": "vcm_os/context/pack_builder/core.py"}),
    ]
    return EvalScenario(
        name="dogfood_token_optimization",
        project_id=pid,
        events=events,
        expected_goals=["reduce VCM pack tokens from 83 to ≤60"],
        expected_decisions=["cut filler sections for general tasks", "keep decisions/errors/code only"],
        expected_errors=["Tests failed: test_t10_vcm_beats_rag"],
        test_query="What was the token optimization goal?",
        expected_answer_keywords=["reduce tokens", "cut filler sections"],
        expected_rationales=["preserve verbatim matching", "protected terms need longer cap"],
        protected_terms=["pack builder", "token budget"],
    )


def session_2_exact_symbol_fix() -> EvalScenario:
    """Real session: fixing exact-symbol loss."""
    pid = "vcm_os_exact"
    sid = "sess_exact_002"
    events = [
        _evt(pid, sid, "user_message",
             "Exact symbols like /api/v2/export/bulk are being truncated at 60 chars. Need to preserve them."),
        _evt(pid, sid, "code_change",
             "Added extract_protected_keywords check in _build_section. Cap = 100 if protected terms found.",
             {"file_path": "vcm_os/context/pack_builder/core.py"}),
        _evt(pid, sid, "user_message",
             "Also need protected_terms in exact scenarios. Added to scenarios_exact.py."),
        _evt(pid, sid, "code_change",
             "Added protected_terms to exact_config_key, exact_api_endpoint, exact_cicd_job, exact_cve.",
             {"file_path": "vcm_os/evals/scenarios/scenarios_exact.py"}),
    ]
    return EvalScenario(
        name="dogfood_exact_symbol_fix",
        project_id=pid,
        events=events,
        expected_goals=["preserve exact symbols like /api/v2/export/bulk"],
        expected_decisions=["cap = 100 if protected terms found", "add protected_terms to exact scenarios"],
        expected_errors=[],
        test_query="How did we fix exact symbol truncation?",
        expected_answer_keywords=["protected terms", "cap = 100"],
        protected_terms=["/api/v2/export/bulk", "scenarios_exact.py"],
    )


def session_3_pso_compact() -> EvalScenario:
    """Real session: compacting PSO slot."""
    pid = "vcm_os_pso"
    sid = "sess_pso_003"
    events = [
        _evt(pid, sid, "user_message",
             "PSO slot uses too many tokens with headers like '### Project State' and 'Active Goals:'. Need inline format."),
        _evt(pid, sid, "code_change",
             "Replaced headers with inline format: g=goal t=task d=dec b=bug f=file c=constraint.",
             {"file_path": "vcm_os/memory/project_state/pack_slot.py"}),
        _evt(pid, sid, "error",
             "proj_state metric dropped to 0.017! Goals are truncated to 25 chars and don't match expected.",
             {"error_kind": "regression"}),
        _evt(pid, sid, "user_message",
             "Fix: increase truncate limit to 60 chars. Ensure section always added even if empty."),
    ]
    return EvalScenario(
        name="dogfood_pso_compact",
        project_id=pid,
        events=events,
        expected_goals=["inline format for PSO slot"],
        expected_decisions=["replace headers with g=goal t=task format"],
        expected_errors=["proj_state metric dropped to 0.017"],
        test_query="What was the PSO compact format?",
        expected_answer_keywords=["inline format", "g=goal"],
        protected_terms=["pack_slot.py", "project_state"],
    )


def session_4_rationale_recall() -> EvalScenario:
    """Real session: implementing real rationale recall."""
    pid = "vcm_os_rationale"
    sid = "sess_rationale_004"
    events = [
        _evt(pid, sid, "user_message",
             "Rationale recall is a stub (0.200). Need real metric that checks expected rationales in pack."),
        _evt(pid, sid, "code_change",
             "Added expected_rationales to EvalScenario. Updated rationale_recall to check expected rationales.",
             {"file_path": "vcm_os/evals/component_metrics_v0_9.py"}),
        _evt(pid, sid, "code_change",
             "Added rationales to auth_refresh_loop scenario events.",
             {"file_path": "vcm_os/evals/scenarios/scenarios_core.py"}),
    ]
    return EvalScenario(
        name="dogfood_rationale_recall",
        project_id=pid,
        events=events,
        expected_goals=["real rationale recall metric"],
        expected_decisions=["add expected_rationales to EvalScenario", "check expected rationales in pack"],
        expected_errors=[],
        test_query="What was the rationale recall implementation?",
        expected_answer_keywords=["expected_rationales", "check rationales"],
        protected_terms=["rationale_recall", "EvalScenario"],
    )


def session_5_dogfooding_setup() -> EvalScenario:
    """Real session: setting up dogfooding harness."""
    pid = "vcm_os_dogfood"
    sid = "sess_dogfood_005"
    events = [
        _evt(pid, sid, "user_message",
             "Need dogfooding script for real VCM-OS sessions. Compare VCM vs RawVerbatim on actual coding tasks."),
        _evt(pid, sid, "code_change",
             "Created dogfood_vcm_os.py with 5 real dev sessions. Measures restore, tokens, rationale recall.",
             {"file_path": "dogfood_vcm_os.py"}),
    ]
    return EvalScenario(
        name="dogfood_dogfooding_setup",
        project_id=pid,
        events=events,
        expected_goals=["dogfooding script for real VCM-OS sessions"],
        expected_decisions=["create dogfood_vcm_os.py", "compare VCM vs RawVerbatim"],
        expected_errors=[],
        test_query="What is the dogfooding script?",
        expected_answer_keywords=["dogfood_vcm_os.py", "real dev sessions"],
        protected_terms=["dogfood_vcm_os.py", "RawVerbatim"],
    )


def run_dogfooding():
    sessions = [
        session_1_token_optimization(),
        session_2_exact_symbol_fix(),
        session_3_pso_compact(),
        session_4_rationale_recall(),
        session_5_dogfooding_setup(),
    ]

    store = SQLiteStore()
    vi = VectorIndex()
    si = SparseIndex()
    writer = MemoryWriter(store, vi, si)
    runner = ExperimentRunner(store, vi, si, writer)

    print("=" * 80)
    print("VCM-OS Dogfooding — 5 Real Dev Sessions")
    print("=" * 80)

    for sc in sessions:
        runner.ingest_scenario(sc)

    results = []
    for sc in sessions:
        pack_vcm = runner.run_vcm(sc)
        pack_raw = runner.run_baseline_raw_verbatim(sc)

        score_vcm = runner.score_pack(pack_vcm, sc)
        score_raw = runner.score_pack(pack_raw, sc)

        results.append({
            "scenario": sc.name,
            "vcm_tokens": score_vcm["token_usage"],
            "raw_tokens": score_raw["token_usage"],
            "vcm_restore": score_vcm["overall_restore"],
            "raw_restore": score_raw["overall_restore"],
            "vcm_quality": score_vcm["quality_score"],
            "raw_quality": score_raw["quality_score"],
            "vcm_rationale": score_vcm.get("rationale_recall", 0.0),
        })

        print(f"\n{sc.name}")
        print(f"  VCM:  restore={score_vcm['overall_restore']:.2f} tokens={score_vcm['token_usage']} quality={score_vcm['quality_score']:.2f}")
        print(f"  RAW:  restore={score_raw['overall_restore']:.2f} tokens={score_raw['token_usage']} quality={score_raw['quality_score']:.2f}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    vcm_tokens = sum(r["vcm_tokens"] for r in results) / len(results)
    raw_tokens = sum(r["raw_tokens"] for r in results) / len(results)
    vcm_restore = sum(r["vcm_restore"] for r in results) / len(results)
    raw_restore = sum(r["raw_restore"] for r in results) / len(results)
    vcm_quality = sum(r["vcm_quality"] for r in results) / len(results)
    raw_quality = sum(r["raw_quality"] for r in results) / len(results)

    print(f"VCM  | restore={vcm_restore:.2f} tokens={vcm_tokens:.0f} quality={vcm_quality:.2f}")
    print(f"RAW  | restore={raw_restore:.2f} tokens={raw_tokens:.0f} quality={raw_quality:.2f}")

    if vcm_restore >= raw_restore and vcm_quality >= raw_quality:
        print("\n✅ VCM passes dogfooding gate")
    else:
        print("\n⚠️ VCM needs more work")


if __name__ == "__main__":
    run_dogfooding()
