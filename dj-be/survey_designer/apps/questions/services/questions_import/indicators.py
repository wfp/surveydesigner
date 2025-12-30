import enum

from django.db.models import Q
from modules.models import Indicator
from questions.models import BaseQuestion
from questions.services.questions_import.base import BaseImport


class IndicatorsImport(BaseImport):
    columns_mapping = {
        "indicator_name": "INDICATOR_NAME",
        "indicator_label": "INDICATOR_LABEL",
        "question_name": "QUESTION_NAME",
    }

    def __init__(self, indicators_sheet, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.work_sheet = indicators_sheet
        self.columns = None
        self.cleaned_data = []
        self.indicators = []

    def _validate_and_set_columns(self):
        columns = []

        for counter, cell in enumerate(self.work_sheet[1], 0):
            if not cell.value:
                continue
            key = self.columns_mapping.get(cell.value.lower())
            if key:
                columns.append((key, counter))
                continue

        if len(self.columns_mapping) != len(columns):
            self.non_form_errors.append(
                "Incorrect indicators spreadsheet. Missing columns."
            )

        self.columns = enum.Enum("COLUMNS", columns)

    def _validate_question_name(self, question_name, processed_questions):
        if question_name not in processed_questions:
            if not BaseQuestion.objects.filter(
                Q(root_question__name=question_name)
                | Q(sub_question__name=question_name)
                | Q(repeat_sections__name=question_name)
            ).exists():
                self.non_form_errors.append(
                    f"Question: {question_name} is not in the system"
                )

    def process(self, processed_root_questions):
        self._validate_and_set_columns()

        for counter, row in enumerate(self.work_sheet.iter_rows(min_row=2), 2):
            indicator_name = self.get_value(row, self.columns.INDICATOR_NAME)
            if not indicator_name:
                continue

            indicator_label = self.get_value(row, self.columns.INDICATOR_LABEL)
            question_name = self.get_value(row, self.columns.QUESTION_NAME)

            self.cleaned_data.append(
                {
                    "indicator_name": indicator_name,
                    "indicator_label": indicator_label,
                    "question_name": question_name,
                }
            )

            self._validate_question_name(question_name, processed_root_questions)

    def create(self, skip_saving=False):
        for data in self.cleaned_data:
            indicator_name = data["indicator_name"]
            indicator_label = data["indicator_label"]
            question_name = data["question_name"]
            if skip_saving:
                self.log_change(Indicator, indicator_name, create=True)
            else:
                question = BaseQuestion.objects.exclude(
                    ~Q(root_question__name=question_name),
                    ~Q(sub_question__name=question_name),
                ).first()

                if not question:
                    question = BaseQuestion.objects.exclude(
                        ~Q(repeat_section__name=question_name),
                    ).first()

                if not question:
                    continue

                indicator, created = self.permissions_based_method(
                    name=indicator_name,
                    defaults={
                        "label": indicator_label,
                    },
                )
                indicator.questions.add(question)

                if created:
                    self.log_addition(indicator)
                    self.indicators.append(data)

        return self.indicators

    @property
    def permissions_based_method(self):
        if self.user.is_global_admins_member or self.user.is_superuser:
            return Indicator.objects.update_or_create
        return Indicator.objects.get_or_create
