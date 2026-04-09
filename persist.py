import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from parser import Problem
from state import RoadmapNode, TeachingState

SAVE_PATH = Path(__file__).parent / ".session.json"


def save_session(
    problems: List[Problem],
    messages: List[dict],
    teaching_state: TeachingState,
    file_name: str,
) -> None:
    data = {
        "file_name": file_name,
        "problems": [asdict(p) for p in problems],
        "messages": messages,
        "teaching_state": {
            "hint_mode": teaching_state.hint_mode,
            "active_node": teaching_state.active_node,
            "initialized": teaching_state.initialized,
            "roadmap": [asdict(n) for n in teaching_state.roadmap],
        },
    }
    SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_session() -> Optional[Dict[str, Any]]:
    if not SAVE_PATH.exists():
        return None
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        problems = [Problem(**p) for p in data["problems"]]
        roadmap = [RoadmapNode(**n) for n in data["teaching_state"]["roadmap"]]
        ts = TeachingState(
            hint_mode=data["teaching_state"]["hint_mode"],
            active_node=data["teaching_state"]["active_node"],
            initialized=data["teaching_state"]["initialized"],
            roadmap=roadmap,
        )
        return {
            "problems": problems,
            "messages": data["messages"],
            "teaching_state": ts,
            "file_name": data["file_name"],
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def clear_session() -> None:
    if SAVE_PATH.exists():
        SAVE_PATH.unlink()
