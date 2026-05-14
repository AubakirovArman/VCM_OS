"""Secret and PII redaction for memory text."""
import re
from typing import List, Optional, Tuple


# Patterns for secrets and sensitive data
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("api_key", re.compile(r"\b(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", re.IGNORECASE)),
    ("secret", re.compile(r"\b(?:secret|client_secret|app_secret)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", re.IGNORECASE)),
    ("token", re.compile(r"\b(?:token|access_token|refresh_token|auth_token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?", re.IGNORECASE)),
    ("password", re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\s]{4,})['\"]?", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE)),
    ("aws_key", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("aws_secret", re.compile(r"\b([0-9a-zA-Z/+]{40})\b")),
    ("github_token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,})\b")),
    ("slack_token", re.compile(r"\b(xox[baprs]-[0-9]{10,13}-[0-9]{10,13}(-[a-zA-Z0-9]{24})?)\b")),
    ("stripe_key", re.compile(r"\b((?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,})\b")),
    ("jwt", re.compile(r"\b(eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*)\b")),
    ("env_var_secret", re.compile(r"\b([A-Z_]*(?:SECRET|KEY|TOKEN|PASSWORD|PASS|AUTH)[A-Z_]*)\s*=\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE)),
    ("connection_string", re.compile(r"(\b(?:postgres|mysql|mongodb|redis|amqp)://[^:]+:)([^@]+)(@.*)", re.IGNORECASE)),
    ("ip_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
]


class SecretRedactor:
    """Redact secrets and PII from text before storing in memory."""

    def __init__(self, replacement: str = "[REDACTED]"):
        self.replacement = replacement
        self.patterns = SECRET_PATTERNS

    def redact(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        result = text
        for name, pattern in self.patterns:
            if name == "connection_string":
                result = pattern.sub(r"\1" + self.replacement + r"\3", result)
            elif name == "env_var_secret":
                result = pattern.sub(r"\1=" + self.replacement, result)
            else:
                result = pattern.sub(self.replacement, result)
        return result

    def has_secrets(self, text: Optional[str]) -> bool:
        if not text:
            return False
        for _name, pattern in self.patterns:
            if pattern.search(text):
                return True
        return False

    def get_secret_types(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        found = []
        for name, pattern in self.patterns:
            if pattern.search(text):
                found.append(name)
        return found
