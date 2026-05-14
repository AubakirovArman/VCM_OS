from typing import Optional

from vcm_os.schemas import MemoryObject
from vcm_os.memory.protected_terms import extract_from_memory, ensure_terms_preserved


class MemoryCompressor:
    def compress(self, mem: MemoryObject, level: int = 2) -> str:
        """
        Compression levels:
        L0: raw
        L1: extractive snippet
        L2: structured object summary (default)
        L3: semantic summary
        L4+: ultra compact
        """
        if level <= 0:
            return mem.raw_text or ""
        if level == 1:
            return self._extractive_snippet(mem)
        if level == 2:
            return self._structured_summary(mem)
        if level >= 3:
            return self._semantic_summary(mem)
        return self._structured_summary(mem)

    def _extractive_snippet(self, mem: MemoryObject) -> str:
        text = mem.raw_text or mem.compressed_summary or ""
        return text[:400]

    def _structured_summary(self, mem: MemoryObject) -> str:
        parts = [f"[{mem.memory_type.upper()}]"]
        if mem.decisions:
            for d in mem.decisions:
                parts.append(f"Decision: {d.statement}")
                if d.rationale:
                    parts.append(f"Why: {d.rationale}")
        if mem.errors_found:
            for e in mem.errors_found:
                parts.append(f"Error ({e.kind}): {e.message[:120]}")
        if mem.file_references:
            parts.append(f"Files: {', '.join(mem.file_references)}")
        if mem.open_questions:
            parts.append(f"Open: {'; '.join(mem.open_questions[:3])}")
        if mem.compressed_summary:
            parts.append(f"Summary: {mem.compressed_summary[:150]}")
        return " ".join(parts)

    def _semantic_summary(self, mem: MemoryObject) -> str:
        """Compact but keyword-preserving: use clean structured fields, no metadata fluff."""
        if mem.semantic_summary:
            result = mem.semantic_summary
        elif mem.compressed_summary and mem.memory_type.value == "code_change":
            # Code changes: preserve the actual change description, not just file list
            result = mem.compressed_summary[:150]
        elif mem.decisions:
            parts = []
            for d in mem.decisions[:2]:
                if d.statement:
                    parts.append(d.statement)
            result = " ".join(parts)
        elif mem.errors_found:
            parts = []
            for e in mem.errors_found[:2]:
                if e.message:
                    parts.append(e.message[:80])
            result = " ".join(parts)
        elif mem.file_references:
            result = "Files: " + ", ".join(mem.file_references[:3])
        elif mem.compressed_summary:
            result = mem.compressed_summary[:150]
        else:
            result = (mem.raw_text or "")[:120]

        # Ensure protected terms survive compression
        terms = extract_from_memory(mem)
        if terms:
            result = ensure_terms_preserved(
                mem.raw_text or mem.compressed_summary or "",
                result,
                terms,
            )
        return result
