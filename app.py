import re
from typing import List

import streamlit as st

from llm import (
    classify_intent,
    extract_problems_from_text,
    generate_initial_roadmap,
    stream_teaching_reply,
    update_roadmap_leaves,
)
from parser import Problem, parse_markdown, parse_pdf
from state import RoadmapNode, TeachingState, reset_state


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
        fname = uploaded.name.lower()
        with st.spinner("Parsing problems..."):
            if fname.endswith(".pdf"):
                raw_text = parse_pdf(uploaded.read())
                problems = extract_problems_from_text(raw_text)
            else:
                text = uploaded.read().decode("utf-8")
                problems = parse_markdown(text)
                if not problems:
                    problems = extract_problems_from_text(text)

        if not problems:
            st.error("Could not extract any problems from the file. Please check the format.")
            return

        st.session_state.problems = problems
        st.session_state.file_name = uploaded.name
        st.session_state.messages = []
        st.session_state.teaching_state = TeachingState()
        st.rerun()


# ---------------------------------------------------------------------------
# Chat page
# ---------------------------------------------------------------------------

PROBLEM_INTENTS = {"concept", "example", "next", "full_solution"}


def _get_stream(user_text: str):
    problems: List[Problem] = st.session_state.problems
    t_state: TeachingState = st.session_state.teaching_state

    with st.spinner("Thinking..."):
        intent = classify_intent(user_text)

        if not t_state.initialized and intent in {"greeting", "topic"}:
            t_state.roadmap = generate_initial_roadmap(problems)
            t_state.initialized = True

    st.session_state._last_intent = intent

    return stream_teaching_reply(
        user_text=user_text,
        intent=intent,
        all_problems=problems,
        hint_mode=t_state.hint_mode,
        chat_history=st.session_state.messages,
    )


def _refresh_roadmap() -> None:
    t_state: TeachingState = st.session_state.teaching_state
    if not t_state.initialized:
        return

    intent = getattr(st.session_state, "_last_intent", "other")
    if intent not in PROBLEM_INTENTS:
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


def _show_chat_page() -> None:
    st.html(SIDEBAR_CSS)
    t_state: TeachingState = st.session_state.teaching_state

    with st.sidebar:
        st.markdown("#### Roadmap")
        if t_state.initialized and t_state.roadmap:
            _render_roadmap(t_state.roadmap, t_state.active_node)
        else:
            st.caption("Say hi to start the lesson!")
        st.divider()
        st.caption(f"File: **{st.session_state.get('file_name', '—')}**")
        if st.button("New lesson", use_container_width=True):
            for key in ["problems", "file_name", "messages", "teaching_state", "_last_intent"]:
                st.session_state.pop(key, None)
            st.rerun()
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            reset_state(t_state)
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
            stream = _get_stream(user_input)
            answer = st.write_stream(stream)

        st.session_state.messages.append({"role": "assistant", "content": _fix_latex(answer)})
        _refresh_roadmap()
        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Tutorial Assistant", page_icon="📖", layout="wide")

    if "problems" not in st.session_state:
        _show_upload_page()
    else:
        _show_chat_page()


if __name__ == "__main__":
    main()
