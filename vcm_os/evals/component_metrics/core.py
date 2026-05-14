"""Core utilities for component metrics."""
import re
from typing import List, Set

from vcm_os.schemas import ContextPack


def pack_text(pack: ContextPack) -> str:
    """Extract all text from a context pack, lowercased."""
    return " ".join(s.content for s in pack.sections).lower()


def pack_memory_ids(pack: ContextPack) -> Set[str]:
    """Collect all memory IDs referenced in a pack."""
    ids = set()
    for sec in pack.sections:
        ids.update(sec.memory_ids)
    return ids


def substring_recall(text: str, terms: List[str]) -> float:
    """Fraction of terms that appear as substrings in text."""
    if not terms:
        return 1.0
    hits = sum(1 for t in terms if t.lower() in text)
    return hits / len(terms)


def substring_precision(text: str, terms: List[str]) -> float:
    """Fraction of terms that appear in text (same as recall for positive lists)."""
    return substring_recall(text, terms)


def stale_penalty(text: str, stale_facts: List[str]) -> float:
    """Count stale facts that leaked into the pack text."""
    if not stale_facts:
        return 0.0
    hits = 0
    for fact in stale_facts:
        pattern = re.compile(r"\b" + re.escape(fact.lower()) + r"\b")
        if pattern.search(text):
            hits += 1
    return hits / len(stale_facts)
