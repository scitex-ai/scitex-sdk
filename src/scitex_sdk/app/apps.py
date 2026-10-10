"""Register SDK App code under a namespaced label.

The persisted ``scitex_app`` model/migration identity (chat sessions and
messages) is owned by :mod:`scitex_sdk.app._chat`; this config keeps a
distinct label so both can install together without a duplicate-label
failure. It carries no models of its own.
"""

from django.apps import AppConfig


class ScitexAppConfig(AppConfig):
    default = True
    name = "scitex_sdk.app"
    label = "scitex_sdk_app"
    verbose_name = "SciTeX App Contract"
    default_auto_field = "django.db.models.BigAutoField"
