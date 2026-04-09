from dataclasses import dataclass, field
from typing import Dict, List, Optional

from parser import Problem


@dataclass
class RoadmapNode:
    label: str
    leaves: List[str] = field(default_factory=list)
    active_leaf: int = -1
    done: bool = False


@dataclass
class TeachingState:
    hint_mode: bool = False
    roadmap: List[RoadmapNode] = field(default_factory=list)
    active_node: int = -1
    initialized: bool = False


def reset_state(state: TeachingState) -> None:
    state.hint_mode = False
    state.roadmap = []
    state.active_node = -1
    state.initialized = False


def lesson_topic(problems: List[Problem]) -> str:
    if not problems:
        return "ODE fundamentals"
    types = {p.ode_type for p in problems}
    if len(types) == 1:
        return next(iter(types))
    return "mixed first-order ODE techniques"
