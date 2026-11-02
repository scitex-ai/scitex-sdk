"""scitex-sdk's declared agent guardrails (federation leaf).

Registered under the ``scitex_dev.hooks`` entry-point group in
pyproject.toml exactly like any downstream package's provider; scitex-dev
aggregates them via ``discover_hooks()`` with no special-casing.

SCOPE. Guardrails about the SDK's own surfaces and contracts — theme
tokens, the component corpus, the mount contract. Guardrails about dev
workflow belong to scitex-dev; about containers to
scitex-agent-container. Each declares its own.
"""

from __future__ import annotations

try:
    from scitex_dev.hooks import HookRule
except ImportError:  # scitex-dev absent: standalone SDK use needs no hooks
    HookRule = None  # type: ignore[assignment,misc]


def provide() -> list:
    """Return scitex-sdk's declared guardrails."""
    if HookRule is None:
        return []
    header = {
        "rule": "Use SDK AppHeader, project dropdown, FilterField, and host frame without local chrome forks.",
        "reason": "App headers, dropdowns, and keyword filters share canonical chrome; viewport frames remain host-owned.",
        "severity": "deny",
        "provider": "scitex-sdk",
        "owner_module": "scitex_sdk",
        "check": "scitex_sdk._header_hook:check_payload",
        "doctrine": "ui/_skills/scitex-ui/40_component-usage-doctrine.md",
    }
    web = {
        "rule": "Declare Web APIs with validated SDK descriptors and owned handler bindings.",
        "reason": "Source validation must not import or activate leaf business code.",
        "severity": "deny",
        "provider": "scitex-sdk",
        "owner_module": "scitex_sdk",
        "check": "scitex_sdk._api_hook:check_payload",
        "doctrine": "app/_skills/scitex-app/24_web-api-contract.md",
    }
    return [
        HookRule(
            id="sdk.web-api-contract",
            event="pre-tool-use",
            matches=("Edit", "Write", "MultiEdit", "write_file", "patch"),
            **web,
        ),
        HookRule(
            id="sdk.web-api-contract-after-shell",
            event="post-tool-use",
            matches=("Bash", "terminal", "apply_patch"),
            **web,
        ),
        HookRule(
            id="sdk.header-contract",
            event="pre-tool-use",
            matches=("Edit", "Write", "MultiEdit", "write_file", "patch"),
            script="hooks/enforce_header.sh",
            **header,
        ),
        HookRule(
            id="sdk.header-contract-after-shell",
            event="post-tool-use",
            matches=("Bash", "terminal", "apply_patch"),
            script="hooks/enforce_header_after.sh",
            **header,
        ),
        HookRule(
            id="sdk.no-unthemed-scrollbar",
            rule="Do not ship scrollbar colours outside the shared "
            "shell/scrollbars.css surface — no raw scrollbar-color / "
            "::-webkit-scrollbar thumb/track colours in leaf CSS, and "
            "no unstyled scroll container that renders OS-default "
            "scrollbars on a themed page.",
            reason="Measured 2026-10-22 (operator): the FigRecipe canvas "
            "shipped a light native scrollbar on the dark theme because "
            "scrollbars were the one chrome surface with no shared home "
            "(UI-105 only banned raw hex, it never provided the tokens). "
            "Per-leaf literals fork by theme; the shared surface tracks "
            "light/dark via workspace tokens.",
            event="pre-tool-use",
            severity="warn",
            matches=("Edit", "Write"),
            provider="scitex-sdk",
            check="scitex_sdk._header_hook:check_scrollbar_payload",
            doctrine="src/scitex_sdk/ui/_skills/scitex-ui/40_component-usage-doctrine.md",
        ),
    ]


__all__ = ["provide"]
