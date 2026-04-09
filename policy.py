from datetime import date
from typing import Dict, List, Tuple

POLICY_VERSION = "v1.1.0"
POLICY_UPDATED_AT = str(date.today())

# Centralized intent routing rules.
INTENT_RULES: List[Tuple[str, str]] = [
    ("greeting", r"\b(hi|hello|hey|yo|good morning|good afternoon|good evening)\b"),
    ("overview", r"\b(what are we learning today|what.*learn today|overview|lesson plan|roadmap|today.?s topic)\b"),
    ("concept", r"\b(concept|theory|definition|intuition|what is|explain why)\b"),
    ("example", r"\b(example|go through|walk through|start problem|pick a problem|try problem)\b"),
    ("next_step", r"\b(next step|what.?s next|continue|go on|next)\b"),
    ("hint", r"\b(hint|clue|nudge|a little help)\b"),
    ("full_solution", r"\b(full solution|complete solution|solve it|entire solution|show all steps)\b"),
]


def get_policy_meta() -> Dict[str, str | int]:
    return {
        "policy_version": POLICY_VERSION,
        "rule_count": len(INTENT_RULES),
        "updated_at": POLICY_UPDATED_AT,
    }

