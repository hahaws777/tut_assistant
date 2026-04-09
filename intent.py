import re
from typing import Optional, Tuple

from llm import classify_intent_fallback


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

    rules = [
        ("greeting", r"\b(hi|hello|hey|yo|good morning|good afternoon|good evening)\b"),
        ("overview", r"\b(what are we learning today|what.*learn today|overview|lesson plan|roadmap|today.?s topic)\b"),
        ("concept", r"\b(concept|theory|definition|intuition|what is|explain why)\b"),
        ("example", r"\b(example|go through|walk through|start problem|pick a problem|try problem)\b"),
        ("next_step", r"\b(next step|what.?s next|continue|go on|next)\b"),
        ("hint", r"\b(hint|clue|nudge|a little help)\b"),
        ("full_solution", r"\b(full solution|complete solution|solve it|entire solution|show all steps)\b"),
    ]
    for intent, pattern in rules:
        if re.search(pattern, text):
            return intent, None, False

    if not enable_llm_fallback:
        return "unknown", None, False

    llm_intent = classify_intent_fallback(user_text)
    if llm_intent in INTENTS:
        return llm_intent, None, True
    return "unknown", None, True

