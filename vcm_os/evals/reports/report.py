import json
from typing import Any, Dict


def generate_report(results: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("VCM-OS v0.5 Evaluation Report")
    lines.append("=" * 70)

    # T10
    if "T10" in results:
        lines.append("\n## T10: VCM vs Baselines")
        t10 = results["T10"]
        for method in ["vcm", "full", "summary", "rag"]:
            if method in t10:
                d = t10[method]
                lines.append(f"\n  {method.upper()}:")
                lines.append(f"    Restore accuracy:    {d.get('restore', 0):.3f}")
                lines.append(f"    Token usage (avg):   {d.get('tokens', 0):.0f}")
                lines.append(f"    Keyword coverage:    {d.get('keywords', 0):.3f}")
                lines.append(f"    Stale penalty:       {d.get('stale', 0):.3f}")
                lines.append(f"    Quality score:       {d.get('quality', 0):.3f}")

        # Compute wins
        vcm_q = t10.get("vcm", {}).get("quality", 0)
        full_q = t10.get("full", {}).get("quality", 0)
        summary_q = t10.get("summary", {}).get("quality", 0)
        rag_q = t10.get("rag", {}).get("quality", 0)
        vcm_tokens = t10.get("vcm", {}).get("tokens", 0)
        full_tokens = t10.get("full", {}).get("tokens", 0)

        lines.append(f"\n  VCM vs Full Context:")
        lines.append(f"    Quality delta:       {vcm_q - full_q:+.3f}")
        reduction = (1 - vcm_tokens / max(full_tokens, 1))
        lines.append(f"    Token reduction:     {reduction*100:.1f}%")
        lines.append(f"    Absolute token OK (≤84): {'YES' if vcm_tokens <= 84 else 'NO'}")
        lines.append(f"    Dynamic reduction OK (≥75%): {'YES' if reduction >= 0.75 else 'NO'}")
        lines.append(f"    VCM beats summary:   {'YES' if vcm_q > summary_q else 'NO'}")
        lines.append(f"    VCM beats RAG:       {'YES' if vcm_q > rag_q else 'NO'}")

    # H03
    if "H03" in results:
        lines.append("\n## H03: Cross-Session Contamination")
        h03 = results["H03"]
        lines.append(f"  Total cross-project memories: {h03.get('total_cross_project_memories', 0)}")
        lines.append(f"  Avg cross per scenario:       {h03.get('avg_cross_per_scenario', 0):.3f}")
        lines.append(f"  Contamination rate:           {h03.get('contamination_rate', 0):.4f}")
        threshold = 0.02
        lines.append(f"  Passes threshold (<{threshold}): {'YES' if h03.get('contamination_rate', 1) < threshold else 'NO'}")

    # S05
    if "S05" in results:
        lines.append("\n## S05: False Memory Insertion")
        s05 = results["S05"]
        lines.append(f"  False decisions found:    {s05.get('false_decisions_found', 0)}")
        lines.append(f"  False decisions rejected: {s05.get('false_decisions_rejected', 0)}")
        lines.append(f"  SQLite active:            {s05.get('sqlite_active', False)}")
        lines.append(f"  False memory rate:        {s05.get('false_memory_rate', 0):.3f}")
        lines.append(f"  Passes threshold (<0.05): {'YES' if s05.get('false_memory_rate', 1) < 0.05 else 'NO'}")

    # F03
    if "F03" in results:
        lines.append("\n## F03: Hybrid Retrieval Benchmark")
        restore_imps = [r.get("restore_improvement", 0) for r in results["F03"]]
        quality_imps = [r.get("quality_improvement", 0) for r in results["F03"]]
        stale_reds = [r.get("stale_reduction", 0) for r in results["F03"]]
        lines.append(f"  Scenarios tested:     {len(results['F03'])}")
        lines.append(f"  Avg restore improve:  {sum(restore_imps)/max(len(restore_imps),1):+.3f}")
        lines.append(f"  Avg quality improve:  {sum(quality_imps)/max(len(quality_imps),1):+.3f}")
        lines.append(f"  Avg stale reduction:  {sum(stale_reds)/max(len(stale_reds),1):+.3f}")
        for i, r in enumerate(results["F03"]):
            lines.append(f"    {r.get('scenario', f'Scenario {i+1}'):30s} rest_h={r.get('hybrid_restore', 0):.3f} rest_v={r.get('vector_only_restore', 0):.3f} qual_h={r.get('hybrid_quality', 0):.3f} qual_v={r.get('vector_only_quality', 0):.3f} stale_h={r.get('hybrid_stale', 0):.3f} stale_v={r.get('vector_only_stale', 0):.3f}")

    # I01
    if "I01" in results:
        lines.append("\n## I01: Project State Restore")
        accs = [r.get("restore_accuracy", 0) for r in results["I01"]]
        avg_acc = sum(accs) / max(len(accs), 1)
        lines.append(f"  Scenarios tested:     {len(results['I01'])}")
        lines.append(f"  Avg restore accuracy: {avg_acc:.3f}")
        lines.append(f"  Passes threshold (0.80): {'YES' if avg_acc >= 0.80 else 'NO'}")
        for i, r in enumerate(results["I01"]):
            lines.append(f"    Scenario {i+1}: acc={r.get('restore_accuracy', 0):.3f}, tokens={r.get('token_usage', 0)}")

    # Helper for extra sections
    def _add_section(title: str, key: str):
        if key not in results:
            return
        lines.append(f"\n## {title}")
        d = results[key]
        for method in ["vcm", "full", "summary", "rag"]:
            if method in d:
                m = d[method]
                lines.append(f"  {method.upper()}:")
                lines.append(f"    Restore accuracy:    {m.get('restore', 0):.3f}")
                lines.append(f"    Token usage (avg):   {m.get('tokens', 0):.0f}")
                lines.append(f"    Keyword coverage:    {m.get('keywords', 0):.3f}")
                lines.append(f"    Stale penalty:       {m.get('stale', 0):.3f}")
                lines.append(f"    Quality score:       {m.get('quality', 0):.3f}")
        per = d.get("per_scenario", [])
        lines.append(f"  Scenarios: {len(per)}")
        for s in per:
            lines.append(f"    {s.get('scenario', '?'):40s} restore={s.get('restore_accuracy', 'N/A')} keywords={s.get('keyword_coverage', 'N/A')}")

    _add_section("Adversarial: Exact-Symbol Survival", "adversarial")
    _add_section("Adversarial Hard: 20+ Distractors", "adversarial_hard")
    _add_section("Real Codebase: Dogfooding", "real_codebase")
    _add_section("Multi-Repo: Realistic Projects", "multi_repo")
    _add_section("Holdout: Frozen Generalization", "holdout")

    lines.append("\n" + "=" * 70)
    report = "\n".join(lines)
    print(report)

    with open("eval_report.txt", "w") as f:
        f.write(report)
    print("\nReport saved to eval_report.txt")
    return report
