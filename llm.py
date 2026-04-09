import json
import os
from typing import Generator, List

from dotenv import load_dotenv
from openai import OpenAI

from parser import Problem
from state import RoadmapNode


load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Configure it in .env first.")
    return OpenAI(api_key=api_key)


def _quick_json(prompt: str) -> dict | list | None:
    client = _get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (resp.choices[0].message.content or "").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_problems_from_text(raw_text: str) -> List[Problem]:
    prompt = (
        "You are extracting problems from a tutorial/exercise document.\n"
        "The following is raw text from a PDF or document.\n"
        "Extract each distinct problem/question/exercise as a separate item.\n\n"
        f"Document text:\n{raw_text[:6000]}\n\n"
        "Return a JSON array where each item has:\n"
        '- "title": a short label like "Problem 1", "Question 2", "Exercise 3" etc.\n'
        '- "statement": the full problem text\n\n'
        "Reply with ONLY valid JSON, no markdown fences. Example:\n"
        '[{"title": "Problem 1", "statement": "Solve dy/dx = xy"}]'
    )
    data = _quick_json(prompt)
    if isinstance(data, list) and len(data) >= 1:
        problems = []
        for item in data:
            if isinstance(item, dict) and "title" in item and "statement" in item:
                problems.append(Problem(title=str(item["title"]), statement=str(item["statement"])))
        if problems:
            return problems
    return [Problem(title="Full Document", statement=raw_text[:3000])]


VALID_INTENTS = {"greeting", "topic", "concept", "example", "next", "full_solution", "other"}


def classify_intent(user_text: str) -> str:
    prompt = (
        "You are an intent classifier for a teaching chatbot.\n"
        "Classify the user message into exactly ONE of these intents:\n"
        "- greeting: greetings like hi, hello, hey, good morning, etc.\n"
        "- topic: asking what we are learning today, what topics, what's the lesson about, etc.\n"
        "- concept: asking to explain the concept, theory, definition, background, etc.\n"
        "- example: asking to look at / jump to / go to / start / try a specific problem, or go through an example, etc.\n"
        "- next: asking for the next step, a hint, continue, go on, what's next, etc.\n"
        "- full_solution: asking for the full solution, complete answer, show all steps, solve it completely, etc.\n"
        "- other: anything that does not fit the above.\n\n"
        f'User message: "{user_text}"\n\n'
        "Reply with ONLY the intent label, nothing else."
    )
    client = _get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (resp.choices[0].message.content or "").strip().lower()
    return raw if raw in VALID_INTENTS else "other"


def generate_initial_roadmap(problems: List[Problem]) -> List[RoadmapNode]:
    problem_desc = "\n".join(
        f"- {p.title}: {p.statement}" for p in problems
    )
    prompt = (
        "You are building a lesson roadmap for a teaching session.\n"
        f"Problems:\n{problem_desc}\n\n"
        "Create a short label (in English, max 8 words) for each problem that will appear as a roadmap node.\n"
        "The label should include the problem number and a brief description of the topic or task.\n\n"
        "Reply with ONLY a JSON array of strings, no markdown fences. Example:\n"
        '["Q1: Solve separable ODE", "Q2: Linear equation with e^x"]'
    )
    data = _quick_json(prompt)
    if isinstance(data, list) and len(data) >= 1:
        return [RoadmapNode(label=str(s)) for s in data]
    return [RoadmapNode(label=f"Q{i+1}: {p.statement[:30]}") for i, p in enumerate(problems)]


def update_roadmap_leaves(
    chat_history: List[dict],
    all_problems: List[Problem],
    current_roadmap: List[RoadmapNode],
) -> dict:
    roadmap_desc = []
    for i, node in enumerate(current_roadmap):
        leaves_str = ", ".join(node.leaves) if node.leaves else "(none)"
        roadmap_desc.append(f"  Node {i}: {node.label} | leaves: [{leaves_str}]")
    roadmap_text = "\n".join(roadmap_desc)

    recent = chat_history[-12:]
    history_text = "\n".join(f'{m["role"]}: {m["content"][:300]}' for m in recent)

    prompt = (
        "You are tracking progress of a teaching session.\n\n"
        f"Current roadmap:\n{roadmap_text}\n\n"
        f"Recent conversation:\n{history_text}\n\n"
        "Based on the conversation, determine:\n"
        "1. active_node: which node index (0-based) the user is MOST RECENTLY working on. "
        "If the user just mentioned or jumped to a new problem (e.g. 'q6', 'problem 3'), "
        "set active_node to THAT new problem even if a previous problem was just finished. "
        "Set to -1 only if the user is just greeting or chatting with no problem context.\n"
        "2. done_nodes: list of ALL node indices where the solution was fully provided or the user confirmed completion "
        "(e.g. said 'good job', 'thanks', 'done', moved on to a different problem). "
        "A problem is done if the assistant gave the final answer/solution for it.\n"
        "3. leaves: sub-step labels (English, short) for the ACTIVE node ONLY. "
        "Only include leaves that have actually been discussed or revealed. "
        "Do NOT pre-generate future steps. "
        "If active_node is -1, leaves MUST be [].\n"
        "4. active_leaf: 0-based index of the leaf currently being worked on. "
        "-1 if no leaf is active or if leaves is empty.\n\n"
        "IMPORTANT: If the conversation is just greetings with no problem work, "
        "return active_node: -1 and leaves: [].\n\n"
        "Reply with ONLY valid JSON:\n"
        '{"active_node": -1, "done_nodes": [], "leaves": [], "active_leaf": -1}'
    )
    data = _quick_json(prompt)
    if not isinstance(data, dict):
        return {"active_node": -1, "done_nodes": [], "leaves": [], "active_leaf": -1}

    return {
        "active_node": data.get("active_node", -1),
        "done_nodes": data.get("done_nodes", []),
        "leaves": data.get("leaves", []),
        "active_leaf": data.get("active_leaf", -1),
    }


def _build_system_prompt(
    intent: str,
    all_problems: List[Problem],
    hint_mode: bool,
) -> str:
    problem_list = "\n".join(
        f"  - {p.title}: {p.statement}" for p in all_problems
    )

    base = (
        "You are an interactive tutorial teaching assistant.\n"
        "You are precise, pedagogical, and friendly.\n"
        "Automatically infer the subject and topic from the problems provided.\n"
        "Stay on topic — only discuss content relevant to the problems.\n\n"
        "CRITICAL LaTeX formatting rules (the UI uses KaTeX):\n"
        "- Inline math: use $...$ only. NEVER use \\(...\\).\n"
        "- Display math: use $$...$$ only. NEVER use \\[...\\].\n"
        "- Always put display math $$ on its own line.\n"
        "- Use \\frac{a}{b} not a/b for fractions in display math.\n"
        "- Use \\int, \\sum, \\ln, \\exp etc. for standard functions.\n\n"
        f"All problems in this lesson:\n{problem_list}\n\n"
        f"Hint mode: {'ON' if hint_mode else 'OFF'}\n\n"
        "The user interacts entirely through chat. "
        "They may mention any problem by name or number. "
        "Pick the appropriate problem based on conversation context.\n\n"
        "ABSOLUTE RULE: NEVER solve or start deriving a problem unless the user EXPLICITLY asks for steps, "
        "a walkthrough, a hint, or a full solution. "
        "When the user simply jumps to / selects / mentions a problem, "
        "ONLY show the problem statement and its type, then ask how to proceed.\n"
    )

    intent_instructions = {
        "greeting": (
            "The user is greeting you.\n"
            "Respond warmly, introduce yourself as the tutorial teaching assistant, "
            "briefly mention what topic we will cover today (infer from the problems), "
            "and invite the user to start learning. Do NOT solve any problem yet."
        ),
        "topic": (
            "The user wants to know what we are learning today.\n"
            "Infer the subject and topic from the problems. "
            "Explain the lesson topic and learning objectives. "
            "Do NOT solve any problem yet."
        ),
        "concept": (
            "The user wants to understand a concept or theory.\n"
            "Infer which concept from the conversation context and the problems.\n"
            "Explain in a structured way: Definition, Key ideas, Standard method, Common mistakes.\n"
            "Do NOT solve the specific problem. Only explain the theory."
        ),
        "example": (
            "The user wants to look at a specific problem.\n"
            "Pick the most relevant problem based on conversation context.\n"
            "Your response must contain ONLY:\n"
            "1. The problem statement (in LaTeX if applicable)\n"
            "2. The problem type identification (one sentence)\n"
            "3. A question asking the user how to proceed\n"
            "ABSOLUTELY DO NOT write any solution, derivation, or steps. "
            "Not even the first step. ZERO solving."
        ),
        "next": (
            "The user wants the next step in the walkthrough.\n"
            "Continue from where the conversation left off.\n"
        )
        + (
            "Hint mode is ON: give only a brief hint (1-2 sentences) without revealing full derivation.\n"
            if hint_mode
            else "Explain the next step in detail with the reasoning and derivation.\n"
        ),
        "full_solution": (
            "The user wants the complete solution.\n"
            "Provide a full, clean derivation or answer from start to finish. "
            "Be thorough and show every step."
        ),
        "other": (
            "The user's message does not match a standard teaching command.\n"
            "Try your best to respond helpfully within the context of the lesson. "
            "If the user mentions a specific problem, show ONLY its statement and type — do NOT solve it. "
            "If the question is a conceptual question, answer it. "
            "If it is truly off-topic, gently redirect to the lesson."
        ),
    }

    base += f"Your task for this turn:\n{intent_instructions[intent]}\n"
    return base


def stream_teaching_reply(
    user_text: str,
    intent: str,
    all_problems: List[Problem],
    hint_mode: bool,
    chat_history: List[dict],
) -> Generator[str, None, None]:
    system_prompt = _build_system_prompt(
        intent=intent,
        all_problems=all_problems,
        hint_mode=hint_mode,
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_text})

    client = _get_client()
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
