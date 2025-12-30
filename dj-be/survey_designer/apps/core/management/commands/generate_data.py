from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from modules.models import Module
from questions.models import BaseQuestion
from surveys.models import SurveyCategory


class Command(BaseCommand):
    """
    Generate data
    """

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            BaseQuestion.objects.exists()
            or Module.objects.exists()
            or SurveyCategory.objects.exists()
        ):
            self.stdout.write(self.style.WARNING("Data already generated."))
            return

        fixtures = [
            "survey_designer/apps/core/fixtures/surveys_fixtures.json",
            "survey_designer/apps/core/fixtures/modules_fixtures.json",
            "survey_designer/apps/core/fixtures/choice_group_fixtures.json",
            "survey_designer/apps/core/fixtures/suffix_fixtures.json",
            "survey_designer/apps/core/fixtures/recall_period_fixtures.json",
        ]

        for fixture in fixtures:
            call_command("loaddata", fixture)

        call_command("generate_questions")
        self.stdout.write(self.style.SUCCESS("Data generated."))
