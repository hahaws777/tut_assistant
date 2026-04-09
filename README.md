# ODE Teaching UI

An interactive Streamlit teaching interface for ODE lessons based on a markdown problem set (problems only, no solutions).

## Features

- Parse problems from `lesson.md`
- Infer ODE type automatically (separable / linear / exact / second-order baseline)
- Chat-driven teaching flow with state machine:
  - greeting/topic overview
  - concept explanation
  - guided example walkthrough
  - next-step or hint-only progression
  - full derivation on request
- Sidebar controls:
  - problem selector
  - hint mode toggle
  - show full solution
  - clear chat

## Project structure

```
ode-teaching-ui/
├── app.py
├── parser.py
├── llm.py
├── state.py
├── lesson.md
├── requirements.txt
└── README.md
```

## Run

1. Ensure `.env` contains:
   - `OPENAI_API_KEY=...`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start app:
   - `streamlit run app.py`

## Teaching flow mapping

- `hi` / `hello` -> topic overview
- `what are we learning today?` -> lesson objective
- `what is the concept?` -> concept explanation only
- `go through an example` -> start guided walkthrough
- `next step` / `hint` -> reveal only next step (or hint if Hint Mode is on)
- `full solution` -> full derivation
