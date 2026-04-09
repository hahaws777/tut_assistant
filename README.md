# Tutorial Assistant

An interactive Streamlit-based teaching assistant that works with **any subject**. Feed it a markdown file with problems, and it becomes an AI tutor that explains concepts, walks through solutions step-by-step, and tracks your progress.

## Features

- **Subject-agnostic**: works for ODE, calculus, linear algebra, physics, or any problem-based tutorial
- **AI-driven**: the AI infers the subject, topic, and problem types automatically from `lesson.md`
- **Dynamic roadmap**: right-side panel shows progress; main nodes generated at start, sub-steps grow as you work through problems
- **Chat-driven teaching flow**:
  - Greeting / topic overview
  - Concept explanation
  - Guided step-by-step walkthrough
  - Hint mode
  - Full solution on request
- **LaTeX support**: inline `$...$` and display `$$...$$` with KaTeX rendering

## Project structure

```
├── app.py            # Streamlit UI + chat logic
├── parser.py         # Markdown problem parser
├── llm.py            # OpenAI API calls (intent, roadmap, teaching)
├── state.py          # Session state & roadmap data structures
├── lesson.md         # Your problems (edit this!)
├── requirements.txt
└── README.md
```

## Quick start

1. Create `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
2. Install:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   streamlit run app.py
   ```

## Lesson format

Edit `lesson.md` with any subject. Each `##` heading becomes a problem:

```markdown
# My Tutorial

## Problem 1
Solve dy/dx = xy

## Problem 2
Find the eigenvalues of matrix A = [[2, 1], [1, 3]]

## Question 3
Explain Newton's second law and apply it to a 5kg block on a 30° incline.
```

## Teaching flow

- `hi` / `hello` → AI greets you, generates roadmap from problems
- `jump to Q2` → shows the problem statement only
- `explain the concept` → theory explanation without solving
- `walk me through it` / `next step` → step-by-step guided walkthrough
- `full solution` → complete derivation/answer
