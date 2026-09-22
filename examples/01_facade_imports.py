"""Minimal scitex-sdk example — the facade import rewrite.

Before (imports from the original distributions)::

    from scitex_app import get_files
    from scitex_ui import get_component

After (identical objects through the unified SDK)::

    from scitex_sdk.app import get_files
    from scitex_sdk.ui import get_component

Run::

    python examples/01_facade_imports.py
"""

from __future__ import annotations

import scitex_app
import scitex_ui
from scitex_sdk import app, ui
from scitex_sdk.app import get_files
from scitex_sdk.ui import get_component


def run() -> None:
    """Show the facade re-exports are the same objects as the originals."""
    assert get_files is scitex_app.get_files
    assert get_component is scitex_ui.get_component
    print(f"scitex_sdk.app hosts {len(app.__all__) - 1} names "
          f"from scitex_app (v{scitex_app.__version__})")
    print(f"scitex_sdk.ui hosts {len(ui.__all__) - 1} names "
          f"from scitex_ui (v{scitex_ui.__version__})")
    print("OK — facade re-exports are identical objects.")


if __name__ == "__main__":
    run()
