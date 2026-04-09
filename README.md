# Tutorial Assistant

A production-style interactive tutoring app built with Streamlit.  
Upload a PDF/Markdown lesson and get a guided tutor with deterministic teaching flow, multi-session persistence, and structured lesson state.

## Features

- **Multi-session persistence (SQLite)**:
  - Create, switch, resume, and delete sessions
  - Each session has a unique `session_id`
  - Per-session persistence includes:
    - messages
    - uploaded lesson/file reference
    - current teaching state
    - current problem index
    - current step index
    - hint mode and hint level
    - roadmap state
- **Explicit teaching state machine**:
  - `IDLE`, `OVERVIEW`, `CONCEPT`, `EXAMPLE_SELECTED`, `STEP_BY_STEP`, `HINT`, `FULL_SOLUTION`
  - Deterministic transitions based on user intent
- **Hybrid intent classification**:
  - Rule-based regex/keyword routing first (fast and deterministic)
  - LLM fallback only when rule-based routing is uncertain
- **Structured lesson representation**:
  - Problems normalized into structured objects with:
    - `id`, `title`, `text`
    - `inferred_topic`, `inferred_type`, `difficulty`
    - optional `source_location`
- **Adaptive hint behavior**:
  - Repeated hint requests increase hint specificity (`hint_level` 0-3)
  - Full solution continues on the same active problem context
- **Roadmap + progress UI**:
  - Dynamic roadmap with node/leaf progress
  - Current teaching state, selected problem, step index shown in sidebar
- **LaTeX support**:
  - Inline `$...$` and display `$$...$$`
  - Auto-fix for `\(...\)` and `\[...\]`
- **Chat export**:
  - Download full chat as Markdown

## Project structure

```text
├── app.py            # Streamlit UI, session controls, chat flow
├── intent.py         # Hybrid intent classifier (rule-first + LLM fallback)
├── llm.py            # LLM extraction/roadmap/reply logic
├── models.py         # Structured data models
├── parser.py         # Markdown parser + PDF extraction + problem normalization
├── state.py          # Teaching state machine + transition logic
├── storage.py        # SQLite session persistence
├── persist.py        # Legacy single-session persistence (kept for compatibility)
├── lesson.md         # Example lesson file
├── requirements.txt
└── README.md
```

## Quick start

1. Create `.env` in project root:

```env
OPENAI_API_KEY=sk-...
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run app:

```bash
streamlit run app.py
```

4. Upload a PDF/Markdown/TXT lesson and start chatting.

## Input format

### Markdown / TXT

Each `##` heading becomes a problem block:

```markdown
# My Tutorial

## Problem 1
Solve dy/dx = xy

## Problem 2
Find the eigenvalues of matrix A = [[2, 1], [1, 3]]

## Question 3
Explain Newton's second law and apply it to a 5kg block on a 30 degree incline.
```

### PDF

Any PDF containing exercises/problems. The app extracts text and builds structured problem objects.

## Intent examples

| User message | Routed intent |
|---|---|
| `hi` | `greeting` |
| `what are we learning today` | `overview` |
| `what is the concept` | `concept` |
| `go through an example` | `example` |
| `next step` | `next_step` |
| `hint` | `hint` |
| `full solution` | `full_solution` |
| `jump to q3` / `problem 3` | `jump_to_problem` |

## Sidebar controls

- **Sessions**: create/switch/delete sessions
- **Roadmap**: visualize progress for current lesson
- **State panel**: current teaching state, problem index, step index, hint level
- **Export chat (.md)**: export current session chat
- **Clear chat**: clear messages and reset teaching state in current session

## Intent Router Offline Evaluation

The project includes an offline intent evaluation script and sample dataset:

- Data: `eval/intent_eval.jsonl`
- Script: `scripts/eval_intent.py`

Run in PowerShell:

```bash
python scripts/eval_intent.py --data eval/intent_eval.jsonl
```

Optional arguments:

```bash
python scripts/eval_intent.py --data eval/intent_eval.jsonl --limit 20
python scripts/eval_intent.py --data eval/intent_eval.jsonl --enable-llm-fallback
```

Notes:

- Default mode does **not** call real OpenAI fallback (`--enable-llm-fallback` is off).
- This helps compare deterministic rule-only routing vs hybrid routing.
- Output includes overall accuracy, per-intent precision/recall/f1, confusion matrix, and fallback rate.

## Security Boundary

This project includes a minimal, engineering-focused prompt injection defense layer:

- **Input sanitization** before LLM calls:
  - remove unsafe control characters
  - truncate overlong input
  - detect suspicious patterns (for example, `ignore previous instructions`)
- **Untrusted lesson data boundary**:
  - lesson/problem text is placed in a clearly separated `UNTRUSTED_LESSON_DATA` section in the system prompt
  - the assistant is instructed to treat lesson content as data, not executable instructions
- **High-risk handling**:
  - set `safety_flag`
  - return a safe refusal message without exposing system instructions
  - log a structured `safety_flagged` event into SQLite events

Notes:

- This is a baseline safety layer for practical robustness, not a complete jailbreak-proof solution.
- The design is intentionally simple and extensible for future rule packs or model-based classifiers.
