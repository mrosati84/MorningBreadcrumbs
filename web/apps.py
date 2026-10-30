from importlib import import_module
from typing import final, override

from django.apps import AppConfig


@final
class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"
    verbose_name = "Morning Breadcrumbs Posts"

    @override
    def ready(self) -> None:
        # Importing the module registers its @receiver handlers.
        _ = import_module("web.signals")
