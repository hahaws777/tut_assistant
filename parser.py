import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Problem:
    title: str
    statement: str


def _split_problem_blocks(markdown_text: str) -> List[tuple[str, str]]:
    pattern = re.compile(r"(?=^##\s+)", re.MULTILINE)
    parts = [p.strip() for p in pattern.split(markdown_text) if p.strip()]

    blocks: List[tuple[str, str]] = []
    for part in parts:
        lines = [line.rstrip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if title.startswith("## ") and body:
            blocks.append((title.replace("## ", "").strip(), body))
    return blocks


def parse_problems(markdown_path: str) -> List[Problem]:
    path = Path(markdown_path)
    text = path.read_text(encoding="utf-8")
    blocks = _split_problem_blocks(text)

    problems: List[Problem] = []
    for title, statement in blocks:
        problems.append(Problem(title=title, statement=statement))
    return problems
