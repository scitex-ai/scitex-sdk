"""scitex_sdk.ui — the UI shell + assets (facade over ``scitex_ui``).

Step 1 re-exports the documented public surface of ``scitex_ui`` by IDENTITY,
so ``from scitex_sdk.ui import get_component`` is the same object as
``from scitex_ui import get_component``. The implementation moves here
gradually after the facade releases; the static/TS/CSS assets stay in
scitex_ui until that move (Django's AppDirectoriesFinder resolves them by the
``scitex_ui`` app label, which the facade does not change).
"""

from __future__ import annotations

from scitex_ui import (
    get_component,
    get_docs_path,
    get_static_dir,
    list_components,
    register_component,
)

__version__ = "0.1.0"  # facade version; the shell's own version is scitex_ui.__version__

__all__ = [
    "get_component",
    "get_docs_path",
    "get_static_dir",
    "list_components",
    "register_component",
    "__version__",
]
