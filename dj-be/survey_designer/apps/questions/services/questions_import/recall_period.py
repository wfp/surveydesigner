import enum

from questions.models import RecallPeriod
from questions.services.questions_import.base import BaseImport, QuestionImportException


class RecallPeriodImport(BaseImport):
    columns_mapping = {
        # "<value in spreadsheet>": "<enum attribute>"
        "name": "NAME",
        "description": "DESCRIPTION",
    }

    def __init__(self, recall_period_sheet, user, organizations, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.work_sheet = recall_period_sheet
        self.columns = None
        self.cleaned_data = []
        self.processed_names = set()
        self.recall_periods = {}
        self.organizations = organizations

    def validate_and_set_columns(self):
        columns = []

        for counter, cell in enumerate(self.work_sheet[1]):
            if not cell.value:
                continue
            key = self.columns_mapping.get(cell.value.lower())
            if key:
                columns.append((key, counter))
                continue

        if len(self.columns_mapping) != len(columns):
            raise QuestionImportException(
                "Incorrect recall periods spreadsheet. Missing columns."
            )

        self.columns = enum.Enum("COLUMNS", columns)

    def process(self):
        try:
            self.validate_and_set_columns()
        except QuestionImportException as error:
            self.non_form_errors.append(str(error))

        for counter, row in enumerate(self.work_sheet.iter_rows(min_row=2), 2):
            name = self.get_value(row, self.columns.NAME)
            if not name:
                continue

            description = self.get_value(row, self.columns.DESCRIPTION)

            self.cleaned_data.append({"name": name, "description": description})

            self.processed_names.add(name)

    def create(self, skip_saving=False):
        for data in self.cleaned_data:
            name = data["name"]
            description = data["description"]

            if skip_saving:
                self.log_change(RecallPeriod, name, create=True)
                recall_period = RecallPeriod.objects.filter(name=name).first()
            else:
                recall_period, created = self.permissions_based_method(
                    name=name,
                    defaults={"description": description, **self.user_tracking_kwargs},
                )
                self.log_addition(recall_period)

            if recall_period:
                self.recall_periods[name] = recall_period

        return self.recall_periods

    @property
    def permissions_based_method(self):
        if self.user.is_global_admins_member or self.user.is_superuser:
            return RecallPeriod.objects.update_or_create
        return RecallPeriod.objects.get_or_create
