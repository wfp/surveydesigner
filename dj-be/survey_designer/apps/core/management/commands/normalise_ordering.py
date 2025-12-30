from django.core.management.base import BaseCommand
from django.db import transaction
from modules.models import Indicator, IndicatorArea, Module, Submodule
from surveys.models import SurveyType


class Command(BaseCommand):
    help = "Normalise the order of model objects."

    # List of models to process
    models_to_normalise = [Indicator, IndicatorArea, Module, Submodule, SurveyType]

    def handle(self, *args, **kwargs):
        for model in self.models_to_normalise:
            self.normalise_order(model)

    def normalise_order(self, model):
        self.stdout.write(f"Normalising order for {model.__name__}...")

        with transaction.atomic():
            for i, obj in enumerate(model.objects.order_by("order", "id"), start=1):
                # Update only if the order is different to minimise database hits
                if obj.order != i:
                    obj.order = i
                    obj.save(update_fields=["order"])

        self.stdout.write(
            self.style.SUCCESS(f"Successfully normalised order for {model.__name__}.")
        )
