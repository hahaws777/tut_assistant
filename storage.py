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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            intent TEXT,
            fallback_used INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER,
            parse_success INTEGER,
            metadata_json TEXT
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


def log_event(
    session_id: str,
    event_type: str,
    intent: Optional[str] = None,
    fallback_used: int = 0,
    latency_ms: Optional[int] = None,
    parse_success: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        event_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    event_id, session_id, event_type, intent, fallback_used,
                    latency_ms, parse_success, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    event_type,
                    intent,
                    int(bool(fallback_used)),
                    latency_ms,
                    parse_success,
                    metadata_json,
                ),
            )
    except Exception:
        return


def get_event_metrics(limit: int = 200) -> Dict[str, float | int]:
    try:
        with _conn() as conn:
            rows = conn.execute(
                """
                SELECT fallback_used, latency_ms, parse_success
                FROM events
                ORDER BY ts DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except Exception:
        return {
            "total_events": 0,
            "fallback_rate": 0.0,
            "avg_latency_ms": 0,
            "parse_failure_count": 0,
        }

    total_events = len(rows)
    if total_events == 0:
        return {
            "total_events": 0,
            "fallback_rate": 0.0,
            "avg_latency_ms": 0,
            "parse_failure_count": 0,
        }

    fallback_count = sum(1 for r in rows if int(r[0] or 0) == 1)
    latency_values = [int(r[1]) for r in rows if r[1] is not None]
    parse_failure_count = sum(1 for r in rows if r[2] is not None and int(r[2]) == 0)

    return {
        "total_events": total_events,
        "fallback_rate": fallback_count / total_events,
        "avg_latency_ms": int(sum(latency_values) / len(latency_values)) if latency_values else 0,
        "parse_failure_count": parse_failure_count,
    }


def fetch_recent_conversation_turns(limit: int = 100, session_id: Optional[str] = None) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    try:
        with _conn() as conn:
            if session_id:
                rows = conn.execute(
                    """
                    SELECT session_id, updated_at, payload
                    FROM sessions
                    WHERE session_id = ?
                    ORDER BY updated_at DESC
                    """,
                    (session_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT session_id, updated_at, payload
                    FROM sessions
                    ORDER BY updated_at DESC
                    """,
                ).fetchall()
    except Exception:
        return []

    for sid, updated_at, payload in rows:
        try:
            data = json.loads(payload)
            messages = data.get("messages", [])
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") != "user":
                    continue
                text = str(msg.get("content", "")).strip()
                if not text:
                    continue
                turns.append(
                    {
                        "session_id": sid,
                        "ts": str(updated_at),
                        "user_text": text,
                    }
                )
                if len(turns) >= limit:
                    return turns
        except (TypeError, json.JSONDecodeError):
            continue

    return turns

