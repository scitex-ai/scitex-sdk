"""Register SDK App code while preserving persisted Django identities."""

from django.apps import AppConfig


class ScitexAppConfig(AppConfig):
    default = True
    name = "scitex_sdk.app"
    label = "scitex_app"
    verbose_name = "SciTeX App Contract"
    default_auto_field = "django.db.models.BigAutoField"
