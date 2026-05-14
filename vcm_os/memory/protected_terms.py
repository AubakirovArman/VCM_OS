"""Extract and preserve critical technical terms during compression.

Protected terms are exact identifiers that must survive compression unchanged:
- file paths
- function/class names
- API endpoints
- config keys / env vars
- package versions
- CVE identifiers
- error codes
- test names
- decision IDs
"""

import re
from typing import List, Set

from vcm_os.schemas import MemoryObject


# Regex patterns for protected terms
PATH_RE = re.compile(r"[\w\-/.]+\.(py|ts|js|tsx|jsx|rs|go|java|cpp|c|h|yaml|yml|json|toml|md|txt|cfg|ini)")
API_RE = re.compile(r"/api/[\w/:-]+")
CVE_RE = re.compile(r"CVE-\d{4}-\d+")
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
CONFIG_KEY_RE = re.compile(r"[A-Z][A-Z_0-9]{2,}")  # FEATURE_AUTH_REFRESH_V2
ENV_VAR_RE = re.compile(r"\$\w+|\$\{\w+\}")
TEST_NAME_RE = re.compile(r"test_\w+|\w+_test\.py")
ERROR_CODE_RE = re.compile(r"ERR_\w+|E\d+|\d{3,4}[A-Z]?")
PACKAGE_RE = re.compile(r"[a-z][a-z0-9_-]*>=?[\d.]+|[a-z][a-z0-9_-]*==[\d.]+")


def extract_protected_terms(text: str) -> List[str]:
    """Extract all protected terms from raw text."""
    terms: Set[str] = set()
    if not text:
        return []

    for pat in [PATH_RE, API_RE, CVE_RE, VERSION_RE, CONFIG_KEY_RE, ENV_VAR_RE, TEST_NAME_RE, ERROR_CODE_RE, PACKAGE_RE]:
        for m in pat.finditer(text):
            terms.add(m.group(0))

    # Also extract camelCase / PascalCase identifiers that look like functions/classes
    for m in re.finditer(r"\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b|\b[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*\b", text):
        word = m.group(0)
        if len(word) > 5 and word not in {"Decision", "Requirement", "Error", "Assistant", "Migration"}:
            terms.add(word)

    return sorted(terms)


def extract_from_memory(mem: MemoryObject) -> List[str]:
    """Extract protected terms from all text fields of a memory object."""
    sources = [
        mem.raw_text or "",
        mem.compressed_summary or "",
        mem.semantic_summary or "",
    ]
    for d in mem.decisions:
        sources.append(d.statement or "")
        sources.append(d.rationale or "")
    for e in mem.errors_found:
        sources.append(e.message or "")
        sources.append(e.root_cause or "")
        sources.append(e.fix_attempt or "")
    for e in mem.entities:
        sources.append(e.name)
    sources.extend(mem.file_references or [])

    terms: Set[str] = set()
    for s in sources:
        terms.update(extract_protected_terms(s))
    return sorted(terms)


def ensure_terms_preserved(original: str, compressed: str, terms: List[str]) -> str:
    """If compressed text lost a protected term, append it."""
    missing = [t for t in terms if t.lower() not in compressed.lower()]
    if missing:
        compressed = compressed.rstrip()
        if compressed and not compressed.endswith("."):
            compressed += "."
        compressed += " Terms: " + ", ".join(missing)
    return compressed
