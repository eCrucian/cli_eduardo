from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ValidationFinding:
    model_id: str
    description: str
    severity: Severity
    flagged_for_review: bool
