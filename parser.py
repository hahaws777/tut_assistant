import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Problem:
    title: str
    statement: str
    ode_type: str


def infer_ode_type(statement: str) -> str:
    s = statement.lower().replace(" ", "")

    if any(token in s for token in ["m(x,y)dx+n(x,y)dy=0", "exact", "∂m/∂y", "∂n/∂x"]):
        return "exact ODE"

    if "y'" in statement.lower() or "dy/dx" in s:
        if re.search(r"y['′]\+[^=]*y=", statement.lower()) or re.search(r"dy/dx\+[^=]*y=", s):
            return "first-order linear ODE"

    if "dy/dx" in s and ("x" in s or "y" in s):
        if any(token in s for token in ["dy/dx=", "dydx="]):
            if re.search(r"dy/dx=.*x.*y|dy/dx=.*y.*x", s):
                return "separable ODE"

    if any(token in s for token in ["d2y/dx2", "y''", "y′′"]):
        return "second-order ODE"

    return "first-order ODE"


def _split_problem_blocks(markdown_text: str) -> List[tuple[str, str]]:
    pattern = re.compile(r"(?=^##\s+Problem\s+\d+)", re.MULTILINE)
    parts = [p.strip() for p in pattern.split(markdown_text) if p.strip()]

    blocks: List[tuple[str, str]] = []
    for part in parts:
        lines = [line.rstrip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if title.lower().startswith("## problem") and body:
            blocks.append((title.replace("## ", "").strip(), body))
    return blocks


def parse_problems(markdown_path: str) -> List[Problem]:
    path = Path(markdown_path)
    text = path.read_text(encoding="utf-8")
    blocks = _split_problem_blocks(text)

    problems: List[Problem] = []
    for title, statement in blocks:
        problems.append(
            Problem(
                title=title,
                statement=statement,
                ode_type=infer_ode_type(statement),
            )
        )
    return problems
