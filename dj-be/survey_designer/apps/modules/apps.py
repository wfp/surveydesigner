from django.apps import AppConfig


class ModulesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules"
    label = "modules"
    verbose_name = "Modules & Indicators"

    def ready(self):
        import modules.signals  # noqa: F401
