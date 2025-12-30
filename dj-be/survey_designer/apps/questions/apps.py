from django.apps import AppConfig


class QuestionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "questions"
    label = "questions"
    verbose_name = "Questions"

    def ready(self):
        import questions.signals  # noqa: F401
