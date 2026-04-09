import re
from dataclasses import dataclass
from typing import List, Optional

from models import ProblemModel


@dataclass
class Problem(ProblemModel):
    @property
    def statement(self) -> str:
        return self.text

    @statement.setter
    def statement(self, value: str) -> None:
        self.text = value


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


def parse_markdown(text: str) -> List[Problem]:
    blocks = _split_problem_blocks(text)
    return [_build_problem(i, t, s) for i, (t, s) in enumerate(blocks)]


def parse_pdf(pdf_bytes: bytes) -> str:
    import fitz  # pymupdf
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def _infer_topic(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ["derivative", "integral", "limit", "function"]):
        return "Calculus"
    if any(k in lowered for k in ["matrix", "vector", "determinant"]):
        return "Linear Algebra"
    if any(k in lowered for k in ["probability", "random", "distribution"]):
        return "Probability"
    return "General"


def _infer_type(text: str) -> str:
    lowered = text.lower()
    if "prove" in lowered:
        return "Proof"
    if "find" in lowered or "solve" in lowered:
        return "Computation"
    if "explain" in lowered or "why" in lowered:
        return "Conceptual"
    return "Exercise"


def _infer_difficulty(text: str) -> Optional[str]:
    words = len(text.split())
    if words < 40:
        return "Easy"
    if words < 120:
        return "Medium"
    return "Hard"


def _build_problem(index: int, title: str, statement: str, source_location: Optional[str] = None) -> Problem:
    return Problem(
        id=f"p{index + 1}",
        title=title,
        text=statement,
        inferred_topic=_infer_topic(statement),
        inferred_type=_infer_type(statement),
        difficulty=_infer_difficulty(statement),
        source_location=source_location,
    )
