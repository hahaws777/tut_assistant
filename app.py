import re
import time
from typing import List

import streamlit as st

from llm import (
    extract_problems_from_text,
    generate_initial_roadmap,
    stream_teaching_reply,
    update_roadmap_leaves,
)
from intent import classify_intent_hybrid
from parser import Problem, parse_markdown, parse_pdf
from policy import get_policy_meta
from sanitizer import sanitize_text
from state import RoadmapNode, TeachingState, apply_transition, reset_state
from storage import (
    create_session_id,
    delete_session,
    get_event_metrics,
    list_sessions,
    load_session,
    log_event,
    save_session,
)


POLICY_META = get_policy_meta()


def _fix_latex(text: str) -> str:
    text = re.sub(r'\\\[\s*', '\n$$\n', text)
    text = re.sub(r'\s*\\\]', '\n$$\n', text)
    text = re.sub(r'\\\(\s*', '$', text)
    text = re.sub(r'\s*\\\)', '$', text)
    return text


SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"] {
    left: auto !important;
    right: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    left: auto !important;
    right: 0 !important;
}
</style>
"""

ROADMAP_CSS = """
<style>
.rm-tree { display: flex; flex-direction: column; gap: 0; padding: 4px 0; }
.rm-main-row { display: flex; align-items: center; gap: 10px; }
.rm-dot {
    width: 24px; height: 24px; min-width: 24px;
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; color: #fff;
}
.rm-d-done { background: #10b981; }
.rm-d-active { background: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.22); }
.rm-d-pending { background: #d1d5db; color: #9ca3af; }
.rm-main-label { font-size: 13px; line-height: 1.3; }
.rm-l-done { color: #10b981; font-weight: 600; }
.rm-l-active { color: #3b82f6; font-weight: 700; }
.rm-l-pending { color: #9ca3af; }
.rm-vline { width: 2px; height: 16px; margin-left: 11px; border-radius: 1px; }
.rm-vl-done { background: #10b981; }
.rm-vl-pending { background: #e5e7eb; }
.rm-leaves { margin-left: 34px; display: flex; flex-direction: column; gap: 2px; padding: 2px 0; }
.rm-leaf { display: flex; align-items: center; gap: 8px; }
.rm-leaf-dot { width: 8px; height: 8px; min-width: 8px; border-radius: 50%; }
.rm-ld-done { background: #10b981; }
.rm-ld-active { background: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.22); }
.rm-ld-pending { background: #d1d5db; }
.rm-leaf-label { font-size: 12px; line-height: 1.2; }
.rm-ll-done { color: #059669; }
.rm-ll-active { color: #2563eb; font-weight: 600; }
.rm-ll-pending { color: #9ca3af; }
</style>
"""


def _render_roadmap(roadmap: List[RoadmapNode], active_node: int) -> None:
    parts: List[str] = []
    for i, node in enumerate(roadmap):
        if node.done:
            dot_cls, label_cls = "rm-d-done", "rm-l-done"
            icon = "✓"
        elif i == active_node:
            dot_cls, label_cls = "rm-d-active", "rm-l-active"
            icon = str(i + 1)
        else:
            dot_cls, label_cls = "rm-d-pending", "rm-l-pending"
            icon = str(i + 1)

        if i > 0:
            vl_cls = "rm-vl-done" if node.done or (i <= active_node and active_node >= 0) else "rm-vl-pending"
            parts.append(f'<div class="rm-vline {vl_cls}"></div>')

        parts.append(
            f'<div class="rm-main-row">'
            f'  <div class="rm-dot {dot_cls}">{icon}</div>'
            f'  <div class="rm-main-label {label_cls}">{node.label}</div>'
            f'</div>'
        )

        if node.leaves:
            leaf_parts: List[str] = []
            for li, leaf in enumerate(node.leaves):
                if li < node.active_leaf:
                    ld, ll = "rm-ld-done", "rm-ll-done"
                elif li == node.active_leaf:
                    ld, ll = "rm-ld-active", "rm-ll-active"
                else:
                    ld, ll = "rm-ld-pending", "rm-ll-pending"
                leaf_parts.append(
                    f'<div class="rm-leaf">'
                    f'  <div class="rm-leaf-dot {ld}"></div>'
                    f'  <div class="rm-leaf-label {ll}">{leaf}</div>'
                    f'</div>'
                )
            parts.append('<div class="rm-leaves">' + "".join(leaf_parts) + "</div>")

    html = ROADMAP_CSS + '<div class="rm-tree">' + "".join(parts) + "</div>"
    st.html(html)


# ---------------------------------------------------------------------------
# Initialization page: upload file
# ---------------------------------------------------------------------------

def _show_upload_page() -> None:
    st.title("📖 Tutorial Assistant")
    st.markdown("Upload a **Markdown** or **PDF** file containing your tutorial problems to get started.")

    uploaded = st.file_uploader(
        "Drop your file here",
        type=["md", "txt", "pdf"],
        label_visibility="collapsed",
    )

    if uploaded is not None:
        parse_success = 0
        fname = uploaded.name.lower()
        with st.spinner("Parsing problems..."):
            if fname.endswith(".pdf"):
                raw_text = parse_pdf(uploaded.read())
                sanitized = sanitize_text(raw_text, max_len=20000)
                problems = extract_problems_from_text(sanitized.text)
                if sanitized.safety_flag:
                    try:
                        log_event(
                            session_id=st.session_state.session_id,
                            event_type="safety_flagged",
                            parse_success=0,
                            metadata={
                                "source": "upload_pdf",
                                "pattern_count": len(sanitized.suspicious_patterns),
                                "patterns": sanitized.suspicious_patterns,
                                "policy_version": POLICY_META["policy_version"],
                            },
                        )
                    except Exception:
                        pass
            else:
                text = uploaded.read().decode("utf-8")
                sanitized = sanitize_text(text, max_len=20000)
                problems = parse_markdown(sanitized.text)
                if not problems:
                    problems = extract_problems_from_text(sanitized.text)
                if sanitized.safety_flag:
                    try:
                        log_event(
                            session_id=st.session_state.session_id,
                            event_type="safety_flagged",
                            parse_success=0,
                            metadata={
                                "source": "upload_text",
                                "pattern_count": len(sanitized.suspicious_patterns),
                                "patterns": sanitized.suspicious_patterns,
                                "policy_version": POLICY_META["policy_version"],
                            },
                        )
                    except Exception:
                        pass

        if not problems:
            try:
                log_event(
                    session_id=st.session_state.session_id,
                    event_type="parse_complete",
                    parse_success=0,
                    metadata={"file_name": uploaded.name},
                )
            except Exception:
                pass
            st.error("Could not extract any problems from the file. Please check the format.")
            return
        parse_success = 1

        st.session_state.problems = problems
        st.session_state.file_name = uploaded.name
        st.session_state.messages = []
        st.session_state.teaching_state = TeachingState()
        try:
            log_event(
                session_id=st.session_state.session_id,
                event_type="parse_complete",
                parse_success=parse_success,
                metadata={"file_name": uploaded.name, "problem_count": len(problems)},
            )
        except Exception:
            pass
        save_session(st.session_state.session_id, problems, [], st.session_state.teaching_state, uploaded.name)
        st.rerun()


# ---------------------------------------------------------------------------
# Chat page
# ---------------------------------------------------------------------------

def _get_stream(user_text: str):
    problems: List[Problem] = st.session_state.problems
    t_state: TeachingState = st.session_state.teaching_state

    safe_input = sanitize_text(user_text, max_len=2000)
    if safe_input.safety_flag:
        st.session_state.safety_flag = True
        try:
            log_event(
                session_id=st.session_state.session_id,
                event_type="safety_flagged",
                intent="unknown",
                metadata={
                    "source": "user_input",
                    "pattern_count": len(safe_input.suspicious_patterns),
                    "patterns": safe_input.suspicious_patterns,
                        "policy_version": POLICY_META["policy_version"],
                },
            )
        except Exception:
            pass
        st.session_state._last_intent = "unknown"
        return iter(
            [
                "I cannot help with requests that try to override system behavior. "
                "Please ask a lesson-related question such as concept, next step, hint, or full solution."
            ]
        )

    st.session_state.safety_flag = False
    with st.spinner("Thinking..."):
        intent, problem_idx, fallback_used = classify_intent_hybrid(safe_input.text)
        try:
            log_event(
                session_id=st.session_state.session_id,
                event_type="intent_classified",
                intent=intent,
                fallback_used=int(fallback_used),
                metadata={
                    "user_text_len": len(safe_input.text),
                    "truncated": safe_input.was_truncated,
                    "policy_version": POLICY_META["policy_version"],
                },
            )
        except Exception:
            pass
        if problem_idx is not None and 0 <= problem_idx < len(problems):
            t_state.current_problem_index = problem_idx
        apply_transition(t_state, intent, problem_idx)

        if not t_state.initialized and intent in {"greeting", "overview"}:
            t_state.roadmap = generate_initial_roadmap(problems)
            t_state.initialized = True

    st.session_state._last_intent = intent

    return stream_teaching_reply(
        user_text=safe_input.text,
        intent=intent,
        all_problems=problems,
        hint_mode=t_state.hint_mode,
        chat_history=st.session_state.messages,
        current_state=t_state.current_state,
        current_problem_index=t_state.current_problem_index,
        current_step_index=t_state.current_step_index,
        hint_level=t_state.hint_level,
    )


def _refresh_roadmap() -> None:
    t_state: TeachingState = st.session_state.teaching_state
    if not t_state.initialized:
        return

    problems: List[Problem] = st.session_state.problems
    data = update_roadmap_leaves(
        st.session_state.messages, problems, t_state.roadmap,
    )

    active = data.get("active_node", -1)
    done_nodes = data.get("done_nodes", [])
    leaves = data.get("leaves", [])
    active_leaf = data.get("active_leaf", -1)

    for idx in done_nodes:
        if 0 <= idx < len(t_state.roadmap):
            t_state.roadmap[idx].done = True

    if 0 <= active < len(t_state.roadmap):
        t_state.active_node = active
        node = t_state.roadmap[active]
        if leaves:
            node.leaves = [str(s) for s in leaves]
            node.active_leaf = max(-1, min(active_leaf, len(node.leaves) - 1))
    elif active == -1:
        t_state.active_node = -1


def _export_chat_md() -> str:
    messages = st.session_state.get("messages", [])
    file_name = st.session_state.get("file_name", "lesson")
    lines = [f"# Tutorial Chat — {file_name}\n"]
    for msg in messages:
        role = "**You**" if msg["role"] == "user" else "**Assistant**"
        lines.append(f"### {role}\n")
        lines.append(msg["content"] + "\n")
        lines.append("---\n")
    return "\n".join(lines)


def _show_chat_page() -> None:
    st.html(SIDEBAR_CSS)
    t_state: TeachingState = st.session_state.teaching_state

    with st.sidebar:
        st.markdown("#### Sessions")
        sessions = list_sessions()
        session_options = {f'{s["title"]} | {s["updated_at"]}': s["session_id"] for s in sessions}
        if session_options:
            current_label = next((k for k, v in session_options.items() if v == st.session_state.session_id), None)
            selected = st.selectbox("Choose session", list(session_options.keys()), index=list(session_options.keys()).index(current_label) if current_label else 0)
            selected_sid = session_options[selected]
            if selected_sid != st.session_state.session_id:
                saved = load_session(selected_sid)
                if saved:
                    st.session_state.session_id = selected_sid
                    st.session_state.problems = saved["problems"]
                    st.session_state.messages = saved["messages"]
                    st.session_state.teaching_state = saved["teaching_state"]
                    st.session_state.file_name = saved["file_name"]
                    st.rerun()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("New session", use_container_width=True):
                st.session_state.session_id = create_session_id()
                for key in ["problems", "file_name", "messages", "teaching_state", "_last_intent"]:
                    st.session_state.pop(key, None)
                st.rerun()
        with c2:
            if st.button("Delete session", use_container_width=True):
                delete_session(st.session_state.session_id)
                st.session_state.session_id = create_session_id()
                for key in ["problems", "file_name", "messages", "teaching_state", "_last_intent"]:
                    st.session_state.pop(key, None)
                st.rerun()
        st.divider()

        st.markdown("#### Metrics")
        metrics = get_event_metrics(limit=200)
        st.caption(f"total_events: **{metrics['total_events']}**")
        st.caption(f"fallback_rate: **{metrics['fallback_rate']:.2%}**")
        st.caption(f"avg_latency_ms: **{metrics['avg_latency_ms']}**")
        st.caption(f"parse_failure_count: **{metrics['parse_failure_count']}**")
        st.caption(f"policy_version: **{POLICY_META['policy_version']}**")
        st.divider()

        st.markdown("#### Roadmap")
        if t_state.initialized and t_state.roadmap:
            _render_roadmap(t_state.roadmap, t_state.active_node)
        else:
            st.caption("Say hi to start the lesson!")
        st.divider()
        st.caption(f"File: **{st.session_state.get('file_name', '—')}**")
        st.caption(f"State: **{t_state.current_state.value}**")
        st.caption(f"Problem: **{t_state.current_problem_index + 1}**")
        st.caption(f"Step: **{t_state.current_step_index}**")
        st.caption(f"Hint level: **{t_state.hint_level}**")
        st.caption(f"Safety flag: **{bool(st.session_state.get('safety_flag', False))}**")

        if st.session_state.get("messages"):
            md_content = _export_chat_md()
            st.download_button(
                "Export chat (.md)",
                data=md_content,
                file_name="tutorial_chat.md",
                mime="text/markdown",
                use_container_width=True,
            )

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            reset_state(t_state)
            save_session(
                st.session_state.session_id,
                st.session_state.problems,
                [],
                t_state,
                st.session_state.get("file_name", ""),
            )
            st.rerun()

    st.title("📖 Tutorial Assistant")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(_fix_latex(message["content"]))

    user_input = st.chat_input("Ask about today's lesson...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            start_time = time.perf_counter()
            stream = _get_stream(user_input)
            answer = st.write_stream(stream)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            try:
                log_event(
                    session_id=st.session_state.session_id,
                    event_type="reply_complete",
                    intent=st.session_state.get("_last_intent"),
                    latency_ms=latency_ms,
                    metadata={
                        "answer_len": len(answer) if isinstance(answer, str) else 0,
                        "policy_version": POLICY_META["policy_version"],
                    },
                )
            except Exception:
                pass

        st.session_state.messages.append({"role": "assistant", "content": _fix_latex(answer)})
        _refresh_roadmap()
        save_session(
            st.session_state.session_id,
            st.session_state.problems,
            st.session_state.messages,
            st.session_state.teaching_state,
            st.session_state.get("file_name", ""),
        )
        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Tutorial Assistant", page_icon="📖", layout="wide")

    if "session_id" not in st.session_state:
        existing = list_sessions()
        st.session_state.session_id = existing[0]["session_id"] if existing else create_session_id()
    if "safety_flag" not in st.session_state:
        st.session_state.safety_flag = False

    if "problems" not in st.session_state:
        saved = load_session(st.session_state.session_id)
        if saved:
            st.session_state.problems = saved["problems"]
            st.session_state.messages = saved["messages"]
            st.session_state.teaching_state = saved["teaching_state"]
            st.session_state.file_name = saved["file_name"]

    if "problems" not in st.session_state:
        _show_upload_page()
    else:
        _show_chat_page()


if __name__ == "__main__":
    main()
