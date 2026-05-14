"""Response verifier v2: comprehensive agent answer validation against memory."""
import re
from typing import Dict, List, Optional, Set

from vcm_os.schemas import ContextPack, MemoryObject, MemoryType, Validity


class ResponseVerifier:
    """Verify that an agent response is consistent with project memory."""

    def __init__(self):
        self.violation_weight = 0.3
        self.warning_weight = 0.05

    def verify(self, response_text: str, pack: ContextPack, memories: List[MemoryObject]) -> Dict:
        violations = []
        warnings = []
        text_lower = response_text.lower()

        # 1. Rejected decision revival (check first to avoid duplicate stale_usage)
        rejected_mems = [m for m in memories if m.memory_type == MemoryType.DECISION and m.validity == Validity.REJECTED]
        for m in rejected_mems:
            dec_text = " ".join(d.statement.lower() for d in (m.decisions or []))
            if dec_text and len(dec_text) > 10 and dec_text in text_lower:
                violations.append({
                    "type": "rejected_decision_revival",
                    "memory_id": m.memory_id,
                    "decision": dec_text,
                    "note": "Response revives a rejected decision",
                })

        # 2. Stale / archived / superseded / disputed fact check (exclude REJECTED — handled above)
        stale_mems = [
            m for m in memories
            if m.validity in (Validity.ARCHIVED, Validity.SUPERSEDED, Validity.DISPUTED)
        ]
        for m in stale_mems:
            summary = (m.compressed_summary or m.raw_text or "").lower()
            if summary and len(summary) > 10 and summary in text_lower:
                violations.append({
                    "type": "stale_usage",
                    "memory_id": m.memory_id,
                    "summary": m.compressed_summary or m.raw_text,
                    "validity": m.validity.value,
                })

        # 3. Invented file check
        pack_files = set()
        for m in memories:
            for f in m.file_references or []:
                pack_files.add(f.lower())
        mentioned_files = re.findall(
            r"[\w\-_/]+\.(py|ts|js|tsx|jsx|rs|go|java|c|cpp|h|yaml|yml|json|toml|md|txt|cfg|ini)",
            response_text, re.IGNORECASE,
        )
        for f in mentioned_files:
            fname = f.lower()
            if fname not in pack_files:
                warnings.append({
                    "type": "unverified_file",
                    "file": f,
                    "note": "File mentioned in response but not in retrieved memories",
                })

        # 4. Invented symbol check
        pack_symbols = set()
        for m in memories:
            for e in m.entities or []:
                if e.name:
                    pack_symbols.add(e.name.lower())
            # Also check compressed_summary for camelCase/PascalCase
            text = (m.compressed_summary or m.raw_text or "")
            for sym in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text):
                if len(sym) > 5 and any(c.isupper() for c in sym):
                    pack_symbols.add(sym.lower())

        mentioned_symbols = re.findall(r"\b[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+\b", response_text)
        for sym in mentioned_symbols:
            if len(sym) <= 6:
                continue
            if sym.lower() not in pack_symbols and sym.lower() not in {f.lower() for f in mentioned_files}:
                warnings.append({
                    "type": "unverified_symbol",
                    "symbol": sym,
                    "note": "Symbol mentioned in response but not in retrieved memories",
                })

        # 5. Citation check
        cited_ids = re.findall(r"mem_[a-z0-9]+", response_text, re.IGNORECASE)
        if not cited_ids and len(response_text) > 200:
            warnings.append({
                "type": "no_citations",
                "note": "Long response without memory citations",
            })

        # 6. Missing citation on specific claims
        claim_patterns = [
            r"we decided to \w+",
            r"the (error|bug|issue) is \w+",
            r"the (test|deployment|build) (passed|failed|succeeded)",
            r"we should use \w+",
            r"the current (phase|status|branch) is \w+",
        ]
        claims_found = []
        for pattern in claim_patterns:
            for match in re.finditer(pattern, text_lower):
                claims_found.append(match.group(0))
        if claims_found and not cited_ids:
            warnings.append({
                "type": "missing_citation_on_claim",
                "note": f"Specific claims found but no citations: {claims_found[:3]}",
            })

        # 7. Tool evidence contradiction
        tool_mems = [m for m in memories if m.source_type.value == "tool_output"]
        for tm in tool_mems:
            tool_summary = (tm.compressed_summary or "").lower()
            # Test contradiction
            if "passed" in tool_summary and "failed" in text_lower:
                if "test" in tool_summary:
                    violations.append({
                        "type": "tool_evidence_mismatch",
                        "memory_id": tm.memory_id,
                        "tool_summary": tm.compressed_summary,
                        "note": "Response says tests failed but tool output says passed",
                    })
            # Deploy contradiction
            if "success" in tool_summary and "deploy" in tool_summary and "failed" in text_lower:
                violations.append({
                    "type": "tool_evidence_mismatch",
                    "memory_id": tm.memory_id,
                    "tool_summary": tm.compressed_summary,
                    "note": "Response says deploy failed but tool output says success",
                })
            # Lint contradiction
            if "0 issues" in tool_summary and "lint" in tool_summary and "error" in text_lower:
                violations.append({
                    "type": "tool_evidence_mismatch",
                    "memory_id": tm.memory_id,
                    "tool_summary": tm.compressed_summary,
                    "note": "Response mentions lint errors but tool output shows 0 issues",
                })

        # 8. Unsupported claim: strong factual assertions not in memory
        strong_assertions = re.findall(
            r"\b(never|always|must|impossible|certainly|definitely)\s+\w+(?:\s+\w+){0,5}",
            text_lower,
        )
        if strong_assertions and not cited_ids:
            warnings.append({
                "type": "unsupported_strong_claim",
                "note": f"Strong assertions without citation: {strong_assertions[:2]}",
            })

        # 9. Cross-project memory leakage
        project_ids_in_memories = {m.project_id for m in memories if m.project_id}
        if pack.project_id and project_ids_in_memories:
            if pack.project_id not in project_ids_in_memories:
                warnings.append({
                    "type": "cross_project_leakage",
                    "note": "Pack project_id does not match any memory project_id",
                })

        # 10. Active decision contradiction (basic negation heuristic)
        active_decisions = [
            m for m in memories
            if m.memory_type == MemoryType.DECISION and m.validity == Validity.ACTIVE
        ]
        negation_markers = ["not", "no longer", "reversed", "cancelled", "abandoned", "dropped"]
        for m in active_decisions:
            dec_text = " ".join(d.statement.lower() for d in (m.decisions or []))
            if dec_text and len(dec_text) > 10:
                # Check if response negates an active decision
                idx = text_lower.find(dec_text[:30])
                if idx >= 0:
                    context = text_lower[max(0, idx - 30):idx + len(dec_text) + 30]
                    if any(neg in context for neg in negation_markers):
                        violations.append({
                            "type": "active_decision_contradiction",
                            "memory_id": m.memory_id,
                            "decision": dec_text,
                            "note": "Response contradicts an active decision",
                        })

        score = 1.0
        score -= len(violations) * self.violation_weight
        score -= len(warnings) * self.warning_weight
        score = max(0.0, score)

        return {
            "score": score,
            "violations": violations,
            "warnings": warnings,
            "violation_count": len(violations),
            "warning_count": len(warnings),
            "passed": len(violations) == 0,
            "checks_run": 10,
        }
