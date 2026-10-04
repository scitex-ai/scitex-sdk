#!/usr/bin/env python3
"""Agentic response envelope: status rules hold, nothing is granted."""

from __future__ import annotations

import pytest

from scitex_sdk.app.agent import (
    AgentResponse,
    AgentResponseError,
    Artifact,
    Question,
)


def test_result_needs_artifacts():
    # Arrange
    # Act
    response = AgentResponse(
        status="result",
        message="Figure created.",
        artifacts=(Artifact(kind="file", name="plot.png", reference="out/plot.png", validation="passed"),),
        receipt={"leaf": "figrecipe"},
    )
    # Assert
    assert response.artifacts[0].name == "plot.png" and response.receipt == {"leaf": "figrecipe"}


def test_result_without_artifacts_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        AgentResponse(status="result", message="Done.", artifacts=())


def test_needs_input_needs_questions():
    # Arrange
    # Act
    response = AgentResponse(
        status="needs_input",
        message="Which column should I plot?",
        questions=(Question(key="column", question="Which column holds the values?"),),
    )
    # Assert
    assert response.questions[0].key == "column"


def test_needs_input_without_questions_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        AgentResponse(status="needs_input", message="Need more.")


def test_unsupported_needs_next_steps():
    # Arrange
    # Act
    response = AgentResponse(
        status="unsupported",
        message="3D rendering is not enabled.",
        next_steps=("Ask for a 2D line plot instead.",),
    )
    # Assert
    assert response.next_steps != ()


def test_unsupported_without_next_steps_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        AgentResponse(status="unsupported", message="No.")


def test_refused_without_next_steps_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        AgentResponse(status="refused", message="Denied.")


def test_failed_without_next_steps_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        AgentResponse(status="failed", message="Crashed.")


def test_unknown_status_refused():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        AgentResponse(status="maybe", message="Hmm.")


def test_file_artifact_needs_reference():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        Artifact(kind="file", name="plot.png")


def test_data_artifact_needs_value():
    # Arrange
    # Act
    # Assert
    with pytest.raises(AgentResponseError):
        Artifact(kind="data", name="summary")


def test_receipt_defaults_to_empty_object():
    # Arrange
    # Act
    response = AgentResponse(status="failed", message="Down.", next_steps=("Retry later.",))
    # Assert
    assert response.receipt == {}


# EOF


def test_next_steps_string_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        AgentResponse(status="failed", message="Down.", next_steps="retry")


def test_next_steps_blank_item_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        AgentResponse(status="failed", message="Down.", next_steps=["  "])


def test_next_steps_null_item_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        AgentResponse(status="failed", message="Down.", next_steps=[None])


def test_file_reference_integer_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        Artifact(kind="file", name="plot.png", reference=42)


def test_file_reference_blank_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        Artifact(kind="file", name="plot.png", reference="  ")


def test_result_with_questions_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        AgentResponse(
            status="result",
            message="Done.",
            artifacts=(Artifact(kind="data", name="s", value="v", validation="not_checked"),),
            questions=(Question(key="k", question="Q?"),),
        )


def test_questions_refused_outside_needs_input():
    # Arrange
    questions = (Question(key="k", question="Q?"),)
    # Act
    refused = 0
    for status, kwargs in (
        ("unsupported", {"next_steps": ("Alt.",)}),
        ("refused", {"next_steps": ("Ask.",)}),
        ("failed", {"next_steps": ("Retry.",)}),
    ):
        try:
            AgentResponse(status=status, message="M.", questions=questions, **kwargs)
        except AgentResponseError:
            refused += 1
    # Assert
    assert refused == 3


def test_validation_arbitrary_string_refused():
    # Arrange
    # Act
    # Assert
    with __import__("pytest").raises(AgentResponseError):
        Artifact(kind="data", name="s", value="v", validation="anything")


def test_validation_explicit_states_accepted():
    # Arrange
    # Act
    states = [
        Artifact(kind="data", name="s", value="v", validation=state).validation
        for state in ("passed", "failed", "not_checked")
    ]
    # Assert
    assert states == ["passed", "failed", "not_checked"]


def test_failed_keeps_partial_artifacts():
    # Arrange
    # Act
    response = AgentResponse(
        status="failed",
        message="Crashed mid-way.",
        artifacts=(Artifact(kind="data", name="partial", value="v", validation="failed"),),
        next_steps=("Inspect the log.",),
        receipt={"leaf": "figrecipe", "error": "boom"},
    )
    # Assert
    assert response.artifacts[0].validation == "failed" and response.receipt["error"] == "boom"
