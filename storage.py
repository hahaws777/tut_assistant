import json
import sqlite3
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from parser import Problem
from state import RoadmapNode, TeachingFlowState, TeachingState

DB_PATH = Path(__file__).parent / "storage" / "sessions.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            payload TEXT NOT NULL
        )
        """
    )
    return conn


def create_session_id() -> str:
    return str(uuid.uuid4())


def save_session(
    session_id: str,
    problems: List[Problem],
    messages: List[dict],
    teaching_state: TeachingState,
    file_name: str,
) -> None:
    payload = {
        "file_name": file_name,
        "problems": [asdict(p) for p in problems],
        "messages": messages,
        "teaching_state": asdict(teaching_state),
    }
    data = json.dumps(payload, ensure_ascii=False)
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, payload, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                payload=excluded.payload,
                updated_at=CURRENT_TIMESTAMP
            """,
            (session_id, data),
        )


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT payload FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
        problems = [Problem(**p) for p in data["problems"]]
        ts_raw = data["teaching_state"]
        roadmap = [RoadmapNode(**n) for n in ts_raw.get("roadmap", [])]
        current_state = ts_raw.get("current_state", TeachingFlowState.IDLE.value)
        if isinstance(current_state, str):
            try:
                current_state = TeachingFlowState(current_state)
            except ValueError:
                current_state = TeachingFlowState.IDLE
        ts = TeachingState(**{**ts_raw, "roadmap": roadmap})
        ts.current_state = current_state
        return {
            "problems": problems,
            "messages": data.get("messages", []),
            "teaching_state": ts,
            "file_name": data.get("file_name", ""),
        }
    except (TypeError, KeyError, json.JSONDecodeError):
        return None


def list_sessions() -> List[Dict[str, str]]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT session_id, updated_at, payload
            FROM sessions
            ORDER BY updated_at DESC
            """
        ).fetchall()
    result: List[Dict[str, str]] = []
    for sid, updated, payload in rows:
        title = sid[:8]
        try:
            p = json.loads(payload)
            file_name = p.get("file_name", "")
            if file_name:
                title = f"{file_name} ({sid[:8]})"
        except (TypeError, json.JSONDecodeError):
            pass
        result.append({"session_id": sid, "updated_at": updated, "title": title})
    return result


def delete_session(session_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

