"""Load Django's real app config only when GUI registration is requested."""

try:
    from django.apps import AppConfig
except ModuleNotFoundError as error:
    if error.name != "django":
        raise
    raise ImportError(
        "Django app registration requires the SDK GUI extra. "
        "Install with: pip install 'scitex-sdk[gui]'"
    ) from error
