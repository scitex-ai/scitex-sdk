#!/usr/bin/env python3
"""Agentic response envelope: one natural-language call, one honest outcome.

Five statuses — ``result``, ``needs_input``, ``unsupported``, ``refused``,
``failed`` — over six flat fields. The envelope describes what happened; it
grants nothing: a router choice or user answer cannot grant source
admission, project access, or action authority, and native authorization
and error behavior are preserved by the leaf, not restated here.

Artifact entries wrap actual leaf references or data (never invented
paths); warnings, partial outputs, and validation states are preserved;
``receipt`` is ``{}`` when nothing executed, otherwise the real execution
metadata with agent and leaf execution recorded separately.

There is deliberately NO router here: choosing an operation from language
needs a genuine model binding (owned by Infra), and a keyword stub would
be a pretend agent. The envelope plus validation is the reversible
protocol half; the router arrives with the binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

STATUSES = ("result", "needs_input", "unsupported", "refused", "failed")

#: Explicit artifact validation states. ``not_checked`` is the honest
#: default: unknown is stated, never a fabricated science pass.
VALIDATION_STATES = ("passed", "failed", "not_checked")


class AgentResponseError(ValueError):
    """An envelope violates its status contract."""


def _require_text(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentResponseError(f"{what} must be a nonempty string")
    return value


@dataclass(frozen=True)
class Artifact:
    """One actual leaf output: a file reference or inline data."""

    kind: str
    name: str
    validation: str = "not_checked"
    scope: str = "unknown"
    reference: str = ""
    media_type: str = ""
    value: Any = None
    sha256: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("file", "data"):
            raise AgentResponseError(
                f"artifact kind must be 'file' or 'data', got {self.kind!r}"
            )
        _require_text(self.name, "artifact name")
        if self.validation not in VALIDATION_STATES:
            raise AgentResponseError(
                f"artifact validation must be one of {VALIDATION_STATES}, "
                f"got {self.validation!r}"
            )
        _require_text(self.scope, "artifact scope")
        if self.kind == "file":
            _require_text(self.reference, "file artifact reference")
        if self.kind == "data" and self.value is None:
            raise AgentResponseError("a data artifact needs a value")


@dataclass(frozen=True)
class Question:
    """One concrete answerable prompt for missing input."""

    key: str
    question: str

    def __post_init__(self) -> None:
        _require_text(self.key, "question key")
        _require_text(self.question, "question text")


@dataclass(frozen=True)
class AgentResponse:
    """The outcome of one natural-language agent call."""

    status: str
    message: str
    artifacts: tuple = ()
    questions: tuple = ()
    next_steps: tuple = ()
    receipt: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise AgentResponseError(
                f"status must be one of {STATUSES}, got {self.status!r}"
            )
        _require_text(self.message, "message")
        if not isinstance(self.artifacts, (list, tuple)):
            raise AgentResponseError("artifacts must be an array")
        if not isinstance(self.questions, (list, tuple)):
            raise AgentResponseError("questions must be an array")
        if not isinstance(self.next_steps, (list, tuple)):
            raise AgentResponseError("next_steps must be an array")
        for step in self.next_steps:
            _require_text(step, "next step")
        for artifact in self.artifacts:
            if not isinstance(artifact, Artifact):
                raise AgentResponseError("artifacts must be Artifact entries")
        for question in self.questions:
            if not isinstance(question, Question):
                raise AgentResponseError("questions must be Question entries")
        if not isinstance(self.receipt, dict):
            raise AgentResponseError("receipt must be an object")
        if self.status == "result" and not self.artifacts:
            raise AgentResponseError("a result needs nonempty artifacts")
        if self.status != "needs_input" and self.questions:
            raise AgentResponseError(
                "only needs_input carries missing-input questions"
            )
        if self.status == "needs_input" and not self.questions:
            raise AgentResponseError("needs_input needs concrete questions")
        if self.status in ("unsupported", "refused", "failed") and not self.next_steps:
            raise AgentResponseError(f"{self.status} needs actionable next_steps")


__all__ = [
    "STATUSES",
    "AgentResponse",
    "AgentResponseError",
    "Artifact",
    "Question",
]


# EOF
