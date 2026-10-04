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


def test_dispatch_without_router_fails_honestly():
    # Arrange
    from scitex_sdk.app.agent import AgentRequest, dispatch
    # Act
    response = dispatch(AgentRequest(text="Plot my data."), ("figrecipe",))
    # Assert
    assert response.status == "failed" and "router" in response.message.lower()


def test_dispatch_forwards_original_text_to_specialist():
    # Arrange
    from scitex_sdk.app.agent import AgentRequest, AgentResponse, Artifact, dispatch
    seen = {}

    def fig_handler(req):
        # Arrange
        seen["text"] = req.text
        # Act
        # Assert
        return AgentResponse(
            status="result",
            message="Figure created.",
            artifacts=(Artifact(kind="file", name="plot.png", reference="out/plot.png", validation="passed"),),
            receipt={"leaf": "figrecipe"},
        )

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    response = dispatch(AgentRequest(text="Plot my data."), {"figrecipe": fig_handler, "stats": None}, router=FixedRouter())
    # Assert
    assert response.status == "result" and seen["text"] == "Plot my data." and response.receipt == {"leaf": "figrecipe"}


def test_dispatch_rejects_out_of_set_choice():
    # Arrange
    from scitex_sdk.app.agent import AgentRequest, dispatch

    class RogueRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "elsewhere"

    # Act
    response = dispatch(AgentRequest(text="Hi."), ("figrecipe",), router=RogueRouter())
    # Assert
    assert response.status == "failed" and response.receipt["choice"] == "elsewhere"


def test_dispatch_rejects_non_router():
    # Arrange
    import pytest as _pytest
    from scitex_sdk.app.agent import AgentRequest, dispatch
    # Act
    # Assert
    with _pytest.raises(AgentResponseError):
        dispatch(AgentRequest(text="Hi."), ("figrecipe",), router=object())


def test_dispatch_invokes_selected_handler_with_original_request():
    # Arrange
    from scitex_sdk.app.agent import AgentRequest, Artifact, dispatch
    seen = {}

    def fig_handler(req):
        # Arrange
        seen["text"] = req.text
        # Act
        # Assert
        return __import__("scitex_sdk.app.agent", fromlist=["AgentResponse"]).AgentResponse(
            status="result",
            message="Figure created.",
            artifacts=(Artifact(kind="file", name="plot.png", reference="out/plot.png", validation="passed"),),
            receipt={"leaf": "figrecipe"},
        )

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    response = dispatch(AgentRequest(text="Plot my data."), {"figrecipe": fig_handler}, router=FixedRouter())
    # Assert
    assert response.status == "result" and seen["text"] == "Plot my data." and response.artifacts[0].name == "plot.png" and response.receipt == {"leaf": "figrecipe"}


def test_dispatch_propagates_handler_failure():
    # Arrange
    from scitex_sdk.app.agent import AgentRequest, AgentResponse, dispatch

    def failing_handler(req):
        # Arrange
        # Act
        # Assert
        return AgentResponse(status="failed", message="Leaf crashed.", next_steps=("Retry.",), receipt={"leaf": "figrecipe"})

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    response = dispatch(AgentRequest(text="Plot."), {"figrecipe": failing_handler}, router=FixedRouter())
    # Assert
    assert response.status == "failed" and response.receipt == {"leaf": "figrecipe"}


def test_dispatch_missing_handler_fails_explicitly():
    # Arrange
    from scitex_sdk.app.agent import AgentRequest, dispatch

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    response = dispatch(AgentRequest(text="Plot."), {"figrecipe": None}, router=FixedRouter())
    # Assert
    assert response.status == "failed" and "callable" in response.message


def test_agent_view_unbound_answers_failed():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view
    # Act
    response = agent_view({})(RequestFactory().post("/", data=_json.dumps({"text": "Hi."}), content_type="application/json"))
    # Assert
    assert response.status_code == 200 and _json.loads(response.content.decode())["status"] == "failed"


def test_agent_view_rejects_non_post():
    # Arrange
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view
    # Act
    response = agent_view({})(RequestFactory().get("/"))
    # Assert
    assert response.status_code == 405


def test_agent_view_missing_text_is_400():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view
    # Act
    response = agent_view({})(RequestFactory().post("/", data=_json.dumps({}), content_type="application/json"))
    # Assert
    assert response.status_code == 400


def test_agent_view_absent_context_defaults():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view
    # Act
    response = agent_view({})(RequestFactory().post("/", data=_json.dumps({"text": "Hi."}), content_type="application/json"))
    # Assert
    assert response.status_code == 200 and _json.loads(response.content.decode())["status"] == "failed"


def test_agent_view_invalid_context_reaches_400():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view
    # Act
    refused = 0
    for bad in (False, 0, "", [], None):
        response = agent_view({})(RequestFactory().post("/", data=_json.dumps({"text": "Hi.", "context": bad}), content_type="application/json"))
        refused += response.status_code == 400
    # Assert
    assert refused == 5


def test_agent_view_router_timeout_yields_failed():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view

    class SlowRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            raise TimeoutError("model timed out")

    # Act
    response = agent_view({"figrecipe": None})(RequestFactory().post("/", data=_json.dumps({"text": "Hi."}), content_type="application/json"))
    # Assert
    assert response.status_code == 200 and _json.loads(response.content.decode())["status"] == "failed"


def test_agent_view_handler_error_yields_failed():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view

    def crashing(req):
        # Arrange
        # Act
        # Assert
        raise RuntimeError("leaf crashed")

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    response = agent_view({"figrecipe": crashing})(RequestFactory().post("/", data=_json.dumps({"text": "Hi."}), content_type="application/json"))
    # Assert
    assert response.status_code == 200 and _json.loads(response.content.decode())["status"] == "failed"


def test_agent_view_unserializable_value_yields_failed():
    # Arrange
    import json as _json
    from django.test import RequestFactory
    from scitex_sdk.app.agent import AgentResponse, Artifact, agent_view

    def weird(req):
        # Arrange
        # Act
        # Assert
        return AgentResponse(status="result", message="Odd.", artifacts=(Artifact(kind="data", name="o", value=object()),), receipt={"r": object()})

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    response = agent_view({"figrecipe": weird})(RequestFactory().post("/", data=_json.dumps({"text": "Hi."}), content_type="application/json"))
    # Assert
    assert response.status_code == 200 and _json.loads(response.content.decode())["status"] == "failed"


def test_agent_view_native_404_propagates():
    # Arrange
    import json as _json
    import pytest as _pytest
    from django.http import Http404
    from django.test import RequestFactory
    from scitex_sdk.app.agent import agent_view

    def missing(req):
        # Arrange
        # Act
        # Assert
        raise Http404("gone")

    class FixedRouter:
        def choose_specialist(self, text, enabled):
            # Arrange
            # Act
            # Assert
            return "figrecipe"

    # Act
    # Assert
    with _pytest.raises(Http404):
        agent_view({"figrecipe": missing}, router=FixedRouter())(RequestFactory().post("/", data=_json.dumps({"text": "Hi."}), content_type="application/json"))
