"""Load Django's real app config only when GUI registration is requested."""

from ._gui_dependency import GUI_INSTALL_HINT

try:
    from django.apps import AppConfig
except ModuleNotFoundError as error:
    if error.name != "django":
        raise
    raise ImportError(GUI_INSTALL_HINT) from error
