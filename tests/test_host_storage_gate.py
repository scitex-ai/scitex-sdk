"""The storage-gate host capability: budget reads and write admission."""

import pytest
from django.test import RequestFactory, override_settings

from scitex_sdk.host import (
    AccessError,
    CapabilityUnavailable,
    ProjectAccess,
    StorageBudget,
    StorageRefused,
    require_storage_write,
    storage_budget,
)


class Gate:
    """A host gate with a byte quota, recording what it was asked."""

    def __init__(self, used=0, quota=100, blocked=False):
        self.used, self.quota, self.blocked, self.asked = used, quota, blocked, []

    def budget(self, project_id, request):
        return StorageBudget(
            used_bytes=self.used,
            quota_bytes=self.quota,
            spend_level="blocked" if self.blocked else "ok",
        )

    def require_storage_write(self, project_id, request, *, incoming_sizes):
        self.asked.append((project_id, list(incoming_sizes)))
        if self.blocked:
            raise StorageRefused("Spend cap reached", 402, code="cap", link="/billing")
        if self.used + sum(incoming_sizes) > self.quota:
            raise StorageRefused("Storage quota exceeded", 413, code="quota")


class Broken:
    def budget(self, project_id, request):
        raise RuntimeError("ledger down")

    def require_storage_write(self, project_id, request, *, incoming_sizes):
        raise RuntimeError("ledger down")


class WrongShape:
    def budget(self, project_id, request):
        return {"used_bytes": 1}


def _raised(call):
    """The exception ``call`` raises, or ``None``."""
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - the tests inspect it
        return exc
    return None


@pytest.fixture
def request_():
    return RequestFactory().get("/")


@pytest.fixture
def writable(tmp_path):
    return ProjectAccess("owner/p", "p", tmp_path, can_write=True)


@pytest.fixture
def read_only(tmp_path):
    return ProjectAccess("owner/p", "p", tmp_path, can_write=False)


def test_budget_reports_remaining_bytes(request_, writable):
    # Arrange
    gate = Gate(used=30, quota=100)
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        budget = storage_budget(request_, writable)
    # Assert
    assert budget.remaining_bytes == 70


def test_budget_carries_the_spend_level(request_, writable):
    # Arrange
    gate = Gate(blocked=True)
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        budget = storage_budget(request_, writable)
    # Assert
    assert budget.spend_level == "blocked"


def test_budget_unknown_fields_stay_unknown():
    # Arrange
    budget = StorageBudget(used_bytes=5)
    # Act
    remaining = budget.remaining_bytes
    # Assert
    assert remaining is None


def test_write_within_quota_is_admitted(request_, writable):
    # Arrange
    gate = Gate(used=30, quota=100)
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        require_storage_write(request_, writable, incoming_sizes=[40, 30])
    # Assert
    assert gate.asked == [("owner/p", [40, 30])]


def test_write_over_quota_is_refused_with_413(request_, writable):
    # Arrange
    gate = Gate(used=90, quota=100)
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(
            lambda: require_storage_write(request_, writable, incoming_sizes=[20])
        )
    # Assert
    assert (type(caught), caught.status, caught.code) == (StorageRefused, 413, "quota")


def test_spend_block_is_refused_with_its_link(request_, writable):
    # Arrange
    gate = Gate(blocked=True)
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(
            lambda: require_storage_write(request_, writable, incoming_sizes=[0])
        )
    # Assert
    assert (caught.status, caught.link) == (402, "/billing")


def test_read_only_access_is_refused_with_403(request_, read_only):
    # Arrange
    gate = Gate()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(
            lambda: require_storage_write(request_, read_only, incoming_sizes=[1])
        )
    # Assert
    assert (type(caught), caught.status) == (AccessError, 403)


def test_read_only_access_never_reaches_the_gate(request_, read_only):
    # Arrange
    gate = Gate()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        _raised(lambda: require_storage_write(request_, read_only, incoming_sizes=[1]))
    # Assert
    assert gate.asked == []


def test_no_gate_refuses_writes_as_unavailable(request_, writable):
    # Arrange
    settings = {"SCITEX_STORAGE_GATE": None}
    # Act
    with override_settings(**settings):
        caught = _raised(
            lambda: require_storage_write(request_, writable, incoming_sizes=[1])
        )
    # Assert
    assert isinstance(caught, CapabilityUnavailable)


def test_no_gate_has_no_budget(request_, writable):
    # Arrange
    settings = {"SCITEX_STORAGE_GATE": None}
    # Act
    with override_settings(**settings):
        caught = _raised(lambda: storage_budget(request_, writable))
    # Assert
    assert isinstance(caught, CapabilityUnavailable)


def test_a_failing_gate_refuses_writes_as_unavailable(request_, writable):
    # Arrange
    gate = Broken()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(
            lambda: require_storage_write(request_, writable, incoming_sizes=[1])
        )
    # Assert
    assert isinstance(caught, CapabilityUnavailable)


def test_a_failing_gate_has_no_budget(request_, writable):
    # Arrange
    gate = Broken()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(lambda: storage_budget(request_, writable))
    # Assert
    assert isinstance(caught, CapabilityUnavailable)


def test_a_malformed_budget_is_unavailable(request_, writable):
    # Arrange
    gate = WrongShape()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(lambda: storage_budget(request_, writable))
    # Assert
    assert isinstance(caught, CapabilityUnavailable)


def test_negative_sizes_are_rejected(request_, writable):
    # Arrange
    gate = Gate()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(
            lambda: require_storage_write(request_, writable, incoming_sizes=[-1])
        )
    # Assert
    assert isinstance(caught, ValueError)


def test_only_an_authorized_project_is_accepted(request_):
    # Arrange
    gate = Gate()
    # Act
    with override_settings(SCITEX_STORAGE_GATE=gate):
        caught = _raised(lambda: storage_budget(request_, "owner/p"))
    # Assert
    assert isinstance(caught, TypeError)
