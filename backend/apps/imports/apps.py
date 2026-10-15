from django.apps import AppConfig


class ImportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.imports"

    def ready(self):
        from . import importers  # noqa: F401  (registers importers)
