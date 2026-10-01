"""Use App and UI through the distribution that owns their implementation."""
from scitex_sdk import app, ui
from scitex_sdk.app import get_files
from scitex_sdk.ui import get_component

def run():
    assert get_files is app.get_files
    assert get_component is ui.get_component
    print(f"SDK {app.__version__}: {len(ui.list_components())} UI components")

if __name__ == "__main__":
    run()
