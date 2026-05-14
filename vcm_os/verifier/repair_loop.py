"""Verifier repair loop — automatically fix insufficient or incorrect responses."""
from typing import Dict, List

from vcm_os.context.auto_expand import PackAutoExpander
from vcm_os.schemas import ContextPack, MemoryObject, MemoryRequest
from vcm_os.verifier import ResponseVerifier


class VerifierRepairLoop:
    """Run verifier on response and trigger repair actions if needed."""

    def __init__(self, auto_expander: PackAutoExpander):
        self.verifier = ResponseVerifier()
        self.auto_expander = auto_expander

    def verify_and_repair(
        self,
        response_text: str,
        request: MemoryRequest,
        pack: ContextPack,
        memories: List[MemoryObject],
    ) -> Dict:
        """Verify response and attempt repair if violations found."""
        result = self.verifier.verify(response_text, pack, memories)

        if result["passed"]:
            return {
                "status": "pass",
                "score": result["score"],
                "response": response_text,
                "repairs": [],
            }

        repairs = []

        # Repair 1: Expand pack if missing keywords or memory types
        if any(v["type"] in ("missing_citation_on_claim", "keyword_gap") for v in result.get("warnings", [])):
            expanded_pack = self.auto_expander.build_with_fallback(request, max_expansions=1)
            repairs.append({
                "type": "pack_expanded",
                "reason": "Missing citations or keywords",
                "old_sufficiency": result["score"],
            })
            # Re-verify with expanded pack
            result = self.verifier.verify(response_text, expanded_pack, memories)
            if result["passed"]:
                return {
                    "status": "pass_after_repair",
                    "score": result["score"],
                    "response": response_text,
                    "repairs": repairs,
                }

        # Repair 2: Flag stale usage for human review
        stale_violations = [v for v in result.get("violations", []) if v["type"] == "stale_usage"]
        if stale_violations:
            repairs.append({
                "type": "stale_flagged",
                "reason": f"{len(stale_violations)} stale facts used",
                "violations": stale_violations,
            })

        # Repair 3: Request more citations
        if any(w["type"] == "no_citations" for w in result.get("warnings", [])):
            repairs.append({
                "type": "citation_requested",
                "reason": "Response lacks memory citations",
            })

        # Repair 4: Contradiction warning
        contradictions = [v for v in result.get("violations", []) if "contradiction" in v["type"]]
        if contradictions:
            repairs.append({
                "type": "contradiction_warning",
                "reason": f"{len(contradictions)} contradictions detected",
                "violations": contradictions,
            })

        return {
            "status": "fail",
            "score": result["score"],
            "response": response_text,
            "repairs": repairs,
            "violations": result.get("violations", []),
            "warnings": result.get("warnings", []),
        }
