import re
from dataclasses import dataclass, field
from typing import List


INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions?",
    r"disregard\s+all\s+above",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+message",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"act\s+as\s+.*system",
]


@dataclass
class SanitizedText:
    text: str
    was_truncated: bool = False
    suspicious_patterns: List[str] = field(default_factory=list)
    safety_flag: bool = False


def _strip_control_chars(value: str) -> str:
    # Keep common whitespace (\n, \r, \t), remove other control chars.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)


def sanitize_text(value: str, max_len: int = 4000) -> SanitizedText:
    cleaned = _strip_control_chars(value or "").strip()
    lowered = cleaned.lower()

    matched: List[str] = []
    for p in INJECTION_PATTERNS:
        if re.search(p, lowered):
            matched.append(p)

    was_truncated = len(cleaned) > max_len
    if was_truncated:
        cleaned = cleaned[:max_len]

    return SanitizedText(
        text=cleaned,
        was_truncated=was_truncated,
        suspicious_patterns=matched,
        safety_flag=len(matched) > 0,
    )

