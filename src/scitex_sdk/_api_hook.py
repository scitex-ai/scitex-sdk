"""Native source-only Web API guard, federated by the existing Dev dispatcher."""

from ._header_hook import _source_changes
from .app._api_contract import scan_web_contract


def check_payload(payload):
    """Validate the proposed declaration and its owned dependency bindings."""
    changed = _source_changes(payload, suffixes={".py", ".toml"})
    if changed is None:
        return []
    root, overlays, targets = changed
    if not any(p.suffix in {".py", ".toml"} for p in targets):
        return []
    return [
        f"PS-SDK-WEB: {f.path}:{f.line}: {f.detail}"
        for f in scan_web_contract(root, overlays=overlays)
    ]
