"""Redact sensitive content from test evidence."""

from __future__ import annotations

import re

_REDACTED = "[REDACTED]"
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_SENSITIVE_KEY_VALUE_PATTERN = re.compile(
    r"(?im)^"
    r"(?P<prefix>"
    r"[A-Z0-9_(). -]*"
    r"(?:API[_ -]?KEY|KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|AUTH|COOKIE|"
    r"SESSION|PRIVATE)"
    r"[A-Z0-9_(). -]*"
    r"\s*[:=]\s*"
    r")"
    r"(?P<value>[^\r\n]+)"
)
_TOKEN_PATTERNS = [
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]+"),
    re.compile(r"\bghp_[A-Za-z0-9_]+"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]+"),
    re.compile(r"\bAKIA[A-Z0-9]+"),
    re.compile(r"\bAIza[A-Za-z0-9_-]+"),
    re.compile(r"\bhf_[A-Za-z0-9_-]+"),
]


def redact_evidence(evidence: str) -> str:
    """Return evidence with sensitive content redacted."""
    redacted = _PRIVATE_KEY_PATTERN.sub(_REDACTED, evidence)
    redacted = _SENSITIVE_KEY_VALUE_PATTERN.sub(
        _redact_sensitive_key_value,
        redacted,
    )

    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(_REDACTED, redacted)

    return redacted


def _redact_sensitive_key_value(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}{_REDACTED}"
