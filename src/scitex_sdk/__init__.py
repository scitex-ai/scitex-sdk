"""scitex-sdk — one project for the app contract + the UI shell.

Step 1 (thin facade):
  - ``scitex_sdk.app`` re-exports ``scitex_app`` (the app contract).
  - ``scitex_sdk.ui`` re-exports ``scitex_ui`` (the UI shell + assets).

Re-exports are the SAME objects as the originals (identity, not copies) —
verified by ``tests/test_facade_identity.py`` — so consumers can switch
``scitex_app`` -> ``scitex_sdk.app`` (and ``scitex_ui`` -> ``scitex_sdk.ui``)
mechanically with zero behavior change. The implementation moves INTO
scitex-sdk gradually after this facade releases; the original distributions
stay as thin compat shims until every consumer has migrated.
"""

from scitex_sdk import app, ui  # noqa: F401

__all__ = ["app", "ui"]
