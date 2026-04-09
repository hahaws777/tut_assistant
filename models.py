from dataclasses import dataclass
from typing import Optional


@dataclass
class ProblemModel:
    id: str
    title: str
    text: str
    inferred_topic: str
    inferred_type: str
    difficulty: Optional[str] = None
    source_location: Optional[str] = None

