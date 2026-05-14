import re
from typing import List, Set

# Protected technical terms that must survive compression
PATH_RE = re.compile(r"[\w\-/]+\.(py|ts|js|yaml|yml|json|toml|md|txt)")
API_RE = re.compile(r"/api/[a-zA-Z0-9_\-/]+")
CONFIG_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+\b")
CVE_RE = re.compile(r"CVE-\d{4}-\d+")
ERROR_CODE_RE = re.compile(r"\b[A-Z][a-z]+Error\b|\b[A-Z_]+_ERROR\b")
ENV_VAR_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")  # overlaps with CONFIG_RE; kept for clarity
FUNCTION_RE = re.compile(r"\b[a-z_][a-zA-Z0-9_]*\(\)")


def extract_protected_keywords(text: str) -> List[str]:
    """Extract technical terms that must survive compression."""
    found: Set[str] = set()
    found.update(PATH_RE.findall(text))
    found.update(API_RE.findall(text))
    found.update(CONFIG_RE.findall(text))
    found.update(VERSION_RE.findall(text))
    found.update(CVE_RE.findall(text))
    found.update(ERROR_CODE_RE.findall(text))
    found.update(FUNCTION_RE.findall(text))
    # Deduplicate and limit
    return sorted(found)[:15]
