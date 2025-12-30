from django.apps import AppConfig


class RequestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "change_requests"
    label = "change_requests"
    verbose_name = "Change Requests"
