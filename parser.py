import re
from dataclasses import dataclass
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


def parse_markdown(text: str) -> List[Problem]:
    blocks = _split_problem_blocks(text)
    return [Problem(title=t, statement=s) for t, s in blocks]


def parse_pdf(pdf_bytes: bytes) -> str:
    import fitz  # pymupdf
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)
