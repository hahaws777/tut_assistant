from dataclasses import dataclass, field
from enum import Enum
from typing import List


@dataclass
class RoadmapNode:
    label: str
    leaves: List[str] = field(default_factory=list)
    active_leaf: int = -1
    done: bool = False


class TeachingFlowState(str, Enum):
    IDLE = "IDLE"
    OVERVIEW = "OVERVIEW"
    CONCEPT = "CONCEPT"
    EXAMPLE_SELECTED = "EXAMPLE_SELECTED"
    STEP_BY_STEP = "STEP_BY_STEP"
    HINT = "HINT"
    FULL_SOLUTION = "FULL_SOLUTION"


@dataclass
class TeachingState:
    hint_mode: bool = False
    hint_level: int = 0
    roadmap: List[RoadmapNode] = field(default_factory=list)
    active_node: int = -1
    initialized: bool = False
    current_state: TeachingFlowState = TeachingFlowState.IDLE
    current_problem_index: int = 0
    current_step_index: int = 0
    last_user_intent: str = "unknown"


def reset_state(state: TeachingState) -> None:
    state.hint_mode = False
    state.hint_level = 0
    state.roadmap = []
    state.active_node = -1
    state.initialized = False
    state.current_state = TeachingFlowState.IDLE
    state.current_problem_index = 0
    state.current_step_index = 0
    state.last_user_intent = "unknown"


INTENT_TO_STATE = {
    "greeting": TeachingFlowState.OVERVIEW,
    "overview": TeachingFlowState.OVERVIEW,
    "concept": TeachingFlowState.CONCEPT,
    "example": TeachingFlowState.EXAMPLE_SELECTED,
    "next_step": TeachingFlowState.STEP_BY_STEP,
    "hint": TeachingFlowState.HINT,
    "full_solution": TeachingFlowState.FULL_SOLUTION,
    "jump_to_problem": TeachingFlowState.EXAMPLE_SELECTED,
}


def apply_transition(state: TeachingState, intent: str, target_problem_index: int | None = None) -> None:
    state.last_user_intent = intent
    if intent in INTENT_TO_STATE:
        state.current_state = INTENT_TO_STATE[intent]

    if target_problem_index is not None and target_problem_index >= 0:
        state.current_problem_index = target_problem_index
        state.current_step_index = 0

    if intent == "next_step":
        state.current_step_index += 1

    if intent == "hint":
        state.hint_level = min(state.hint_level + 1, 3)
        state.hint_mode = True
    elif intent == "full_solution":
        state.hint_mode = False
    elif intent in {"example", "jump_to_problem"}:
        state.hint_level = 0
        state.hint_mode = False
    elif intent in {"overview", "concept", "greeting"}:
        state.hint_mode = False
