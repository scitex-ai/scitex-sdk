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
from typing import Any, Optional, Protocol, runtime_checkable

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


@dataclass(frozen=True)
class AgentRequest:
    """One natural-language call: original text, unchanged, plus context."""

    text: str
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.text, "request text")
        if not isinstance(self.context, dict):
            raise AgentResponseError("request context must be an object")


@runtime_checkable
class AgentRouter(Protocol):
    """The injectable decision binding: choose a specialist, forward unchanged.

    Implemented by the neutral runtime (Infra-owned), never by keyword
    matching here: a hardcoded selector would be a pretend agent. Takes the
    original request text plus the enabled specialist IDs and returns the
    chosen specialist ID, which must be one of the enabled set. Any model,
    transport, or credential concern lives with the implementation.
    """

    def choose_specialist(self, text: str, enabled: tuple) -> str:
        """Return exactly one ID from ``enabled`` for ``text``."""


def dispatch(
    request: AgentRequest,
    specialists: dict,
    *,
    router: Optional[AgentRouter] = None,
) -> AgentResponse:
    """Route one request to its specialist and return the real response.

    ``specialists`` maps enabled specialist ID to its operation callable,
    which takes the :class:`AgentRequest` and returns an
    :class:`AgentResponse` (server-injected; typically an admitted leaf
    operation adapted to this contract). Without an injected ``router``
    there is no decision to make: returns ``failed`` naming the missing
    binding rather than fabricating a choice. With one, the original
    request goes unchanged to the chosen specialist's callable and its
    actual response — artifacts, partials, errors alike — propagates.
    Out-of-set choices and missing handlers fail explicitly.
    """
    if router is None:
        return AgentResponse(
            status="failed",
            message="No agent router is bound.",
            next_steps=("Bind a neutral model router before calling.",),
            receipt={},
        )
    if not isinstance(router, AgentRouter):
        raise AgentResponseError("router must implement AgentRouter")
    enabled = tuple(specialists)
    chosen = router.choose_specialist(request.text, enabled)
    if chosen not in tuple(enabled):
        return AgentResponse(
            status="failed",
            message="The router chose an unsupported specialist.",
            next_steps=("Rebind a router that only selects enabled specialists.",),
            receipt={"choice": str(chosen)},
        )
    handler = specialists[chosen]
    if not callable(handler):
        return AgentResponse(
            status="failed",
            message=f"The {chosen} specialist has no callable operation.",
            next_steps=("Register a callable operation for the specialist.",),
            receipt={"specialist": chosen},
        )
    response = handler(request)
    if not isinstance(response, AgentResponse):
        return AgentResponse(
            status="failed",
            message=f"The {chosen} specialist returned no valid response.",
            next_steps=("Fix the specialist operation to return an AgentResponse.",),
            receipt={"specialist": chosen},
        )
    return response


def agent_view(specialists: dict, *, router: Optional[AgentRouter] = None) -> Any:
    """Build the minimal loopback POST wrapper around :func:`dispatch`.

    Accepts ``{"text": ..., "context": {...}}`` JSON and returns the
    envelope JSON. Django is imported lazily so this module stays usable
    without it; without Django there is no wrapper to build. Unbound
    routers answer honest ``failed`` through the same path — the wrapper
    adds transport only, never decisions.
    """
    import json as _json

    try:
        from django.http import HttpResponseNotAllowed, JsonResponse
    except ImportError as exc:
        raise ImportError("the agent view requires Django") from exc

    def view(request: Any):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        try:
            payload = _json.loads(request.body or b"{}")
        except ValueError:
            payload = None
        if not isinstance(payload, dict) or not payload.get("text"):
            return JsonResponse({"error": "text is required"}, status=400)
        try:
            agent_request = AgentRequest(
                text=payload["text"],
                context=payload["context"] if "context" in payload else {},
            )
        except AgentResponseError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        response = dispatch(agent_request, specialists, router=router)
        return JsonResponse(
            {
                "status": response.status,
                "message": response.message,
                "artifacts": [
                    {
                        "kind": a.kind,
                        "name": a.name,
                        "validation": a.validation,
                        "scope": a.scope,
                        "reference": a.reference,
                        "media_type": a.media_type,
                        "value": a.value,
                        "sha256": a.sha256,
                    }
                    for a in response.artifacts
                ],
                "questions": [
                    {"key": q.key, "question": q.question} for q in response.questions
                ],
                "next_steps": list(response.next_steps),
                "receipt": response.receipt,
            }
        )

    return view


__all__ = [
    "STATUSES",
    "AgentRequest",
    "AgentResponse",
    "AgentResponseError",
    "AgentRouter",
    "Artifact",
    "Question",
    "agent_view",
    "dispatch",
]


# EOF
