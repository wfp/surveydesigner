import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from modules.models import (
    Module,
    Submodule,
    SubmoduleMapping,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
)
from organization.models import Organization
from surveys.models import SurveyCategory, SurveyMode, SurveyType


class Command(BaseCommand):
    help = "Initialize organization-scoped content required by E2E tests."

    @staticmethod
    def _attach_default_organization():
        default_organization = Organization.objects.get(
            name=settings.INITIAL_ORGANIZATION
        )
        for model in (
            SurveyCategory,
            SurveyMode,
            SurveyType,
            Module,
        ):
            for item in model.objects.all().iterator():
                item.organizations.add(default_organization)

    @staticmethod
    def _initialize_default_mappings():
        if SubmoduleMapping.objects.exists():
            return

        survey_type = SurveyType.objects.order_by("id").first()
        survey_mode = SurveyMode.objects.order_by("id").first()
        if not survey_type or not survey_mode:
            return

        question_submodules = Submodule.objects.filter(
            root_questions__isnull=False
        ).distinct()
        for submodule in question_submodules.iterator():
            mapping = SubmoduleMapping.objects.create()
            submodule.mapping = mapping
            submodule.save(update_fields=("mapping",))
            mapping.survey_categories.add(survey_type.category)
            type_mapping = SubmoduleMappingSurveyType.objects.create(
                submodule_mapping=mapping,
                survey_type=survey_type,
            )
            SubmoduleMappingSurveyMode.objects.create(
                survey_type=type_mapping,
                survey_mode=survey_mode,
            )

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            os.environ.get("E2E_INIT_DATA", "").lower() != "true"
            or settings.ENV not in ("ci", "test")
            or not settings.ENABLE_E2E_AUTH
        ):
            raise CommandError("E2E data initialization is disabled.")

        self._attach_default_organization()
        self._initialize_default_mappings()
        self.stdout.write(self.style.SUCCESS("E2E data initialized."))
