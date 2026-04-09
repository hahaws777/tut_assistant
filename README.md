# Tutorial Assistant

An interactive Streamlit-based teaching assistant that works with **any subject**. Upload a PDF or Markdown file with problems, and it becomes an AI tutor that explains concepts, walks through solutions step-by-step, and tracks your progress with a dynamic roadmap.

## Features

- **Subject-agnostic**: works for ODE, calculus, linear algebra, physics, or any problem-based tutorial
- **File upload**: drag & drop PDF, Markdown, or TXT — the AI extracts problems automatically
- **AI-driven intent & roadmap**: all classification, roadmap generation, and teaching responses are handled by GPT
- **Dynamic roadmap** (right sidebar):
  - Main nodes generated from your problems on greeting
  - Sub-step leaves grow dynamically as you work through each problem
  - Problems marked complete when solved or when you move on
- **Chat-driven teaching flow**:
  - Greeting / topic overview
  - Concept explanation (theory only, no solving)
  - Jump to any problem by name or number
  - Guided step-by-step walkthrough
  - Full solution on request
- **LaTeX support**: inline `$...$` and display `$$...$$` with KaTeX rendering + auto-fix for `\(...\)` and `\[...\]`
- **Persistent session**: chat history and roadmap survive browser refresh (saved to `.session.json`)
- **Export**: download the full chat as a Markdown file

## Project structure

```
├── app.py            # Streamlit UI, upload page, chat page
├── parser.py         # Markdown parser + PDF text extraction (pymupdf)
├── llm.py            # OpenAI API: intent classifier, roadmap, teaching replies
├── state.py          # Session state & roadmap data structures
├── persist.py        # Save/load session to disk (.session.json)
├── lesson.md         # Example problems (optional, can upload instead)
├── requirements.txt
└── README.md
```

## Quick start

1. Create `.env` in the project folder:

```
OPENAI_API_KEY=sk-...
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
streamlit run app.py
```

4. Upload a PDF or Markdown file on the welcome page, then start chatting.

## Input formats

### Markdown / TXT

Each `##` heading becomes a problem:

```markdown
# My Tutorial

## Problem 1
Solve dy/dx = xy

## Problem 2
Find the eigenvalues of matrix A = [[2, 1], [1, 3]]

## Question 3
Explain Newton's second law and apply it to a 5kg block on a 30° incline.
```

### PDF

Any PDF with problems/exercises. The AI reads the text and extracts each problem automatically — no special formatting required.

## Teaching flow

| You say | Assistant does |
|---|---|
| `hi` / `hello` | Greets you, generates roadmap from problems |
| `what are we learning today?` | Explains topic and learning objectives |
| `jump to Q3` | Shows the problem statement only, asks how to proceed |
| `explain the concept` | Theory explanation without solving |
| `walk me through it` | Starts step-by-step guided walkthrough |
| `next step` | Reveals the next step only |
| `full solution` | Complete derivation / answer |
| `good job` / moves to next problem | Marks current problem as done |

## Sidebar controls

- **Roadmap**: visual progress tracker with main nodes + sub-step leaves
- **Export chat (.md)**: download full conversation as Markdown
- **New lesson**: return to upload page with a fresh session
- **Clear chat**: reset conversation but keep the same file
