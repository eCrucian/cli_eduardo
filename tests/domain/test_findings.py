from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cli_eduardo.domain.findings import Severity, ValidationFinding


def test_severity_values() -> None:
    assert Severity.LOW.value == "low"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.HIGH.value == "high"


def test_severity_from_string() -> None:
    assert Severity("high") is Severity.HIGH


def test_severity_invalid_raises() -> None:
    with pytest.raises(ValueError):
        Severity("critical")


def test_finding_is_frozen() -> None:
    finding = ValidationFinding("m1", "desc", Severity.LOW, False)
    with pytest.raises(FrozenInstanceError):
        finding.description = "changed"  # type: ignore[misc]


def test_finding_equality() -> None:
    assert ValidationFinding("m1", "desc", Severity.LOW, False) == ValidationFinding(
        "m1", "desc", Severity.LOW, False
    )


def test_finding_inequality_on_severity() -> None:
    assert ValidationFinding("m1", "desc", Severity.LOW, False) != ValidationFinding(
        "m1", "desc", Severity.HIGH, False
    )


def test_finding_inequality_on_flagged() -> None:
    assert ValidationFinding("m1", "desc", Severity.LOW, False) != ValidationFinding(
        "m1", "desc", Severity.LOW, True
    )
