import re
from typing import Optional, Tuple

from llm import classify_intent_fallback
from policy import INTENT_RULES


INTENTS = {
    "greeting",
    "overview",
    "concept",
    "example",
    "next_step",
    "hint",
    "full_solution",
    "jump_to_problem",
    "unknown",
}


def _match_problem_index(text: str) -> Optional[int]:
    patterns = [
        r"\b(?:jump to|go to|problem|q|question|exercise)\s*#?\s*(\d{1,3})\b",
        r"\b(\d{1,3})\s*(?:th)?\s*(?:problem|question|exercise)\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            idx = int(m.group(1)) - 1
            if idx >= 0:
                return idx
    return None


def classify_intent_hybrid(user_text: str, enable_llm_fallback: bool = True) -> Tuple[str, Optional[int], bool]:
    text = user_text.strip().lower()
    if not text:
        return "unknown", None, False

    problem_idx = _match_problem_index(text)
    if problem_idx is not None:
        return "jump_to_problem", problem_idx, False

    for intent, pattern in INTENT_RULES:
        if re.search(pattern, text):
            return intent, None, False

    if not enable_llm_fallback:
        return "unknown", None, False

    llm_intent = classify_intent_fallback(user_text)
    if llm_intent in INTENTS:
        return llm_intent, None, True
    return "unknown", None, True

