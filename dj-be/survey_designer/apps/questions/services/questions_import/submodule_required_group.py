import enum

from modules.models import Submodule, SubmoduleMapping, SubmoduleRequiredGroup
from questions.models import RecallPeriod, Suffix
from questions.services.questions_import.base import BaseImport, QuestionImportException


class SubmoduleRequiredGroupImport(BaseImport):
    columns_mapping = {
        "submodule_name": "SUBMODULE_NAME",
        "suffix1": "SUFFIX",
        "suffix2": "SUFFIX_2",
        "recall_period": "RECALL_PERIOD",
    }

    def __init__(self, required_groups_sheet, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.work_sheet = required_groups_sheet
        self.columns = None
        self.cleaned_data = []
        self.group_mappings = []

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
                "Incorrect required groups spreadsheet. Missing columns."
            )

        self.columns = enum.Enum("COLUMNS", columns)

    def process(self):
        try:
            self.validate_and_set_columns()
        except QuestionImportException as error:
            self.non_form_errors.append(str(error))

        for counter, row in enumerate(self.work_sheet.iter_rows(min_row=2), 2):
            submodule = self.get_value(row, self.columns.SUBMODULE_NAME)
            if not submodule:
                continue

            suffix = self.get_value(row, self.columns.SUFFIX)
            suffix_2 = self.get_value(row, self.columns.SUFFIX_2)
            recall_period = self.get_value(row, self.columns.RECALL_PERIOD)

            if not suffix and not suffix_2 and not recall_period:
                continue

            self.cleaned_data.append(
                {
                    "submodule": submodule,
                    "suffix": suffix,
                    "suffix_2": suffix_2,
                    "recall_period": recall_period,
                }
            )

    def create(self, skip_saving=False):
        for data in self.cleaned_data:
            submodule_name = data["submodule"]
            suffix_name = data["suffix"]
            suffix_2_name = data["suffix_2"]
            recall_period_name = data["recall_period"]

            submodule = Submodule.objects.filter(name__iexact=submodule_name).first()
            suffix = Suffix.objects.filter(name__iexact=suffix_name).first()
            suffix_2 = Suffix.objects.filter(name__iexact=suffix_2_name).first()
            recall_period = RecallPeriod.objects.filter(
                name__iexact=recall_period_name
            ).first()

            if skip_saving:
                if submodule is None or not submodule.mapping_id:
                    self.log_change(SubmoduleMapping, submodule_name, create=True)
            else:
                submodule_mapping = submodule.mapping
                created = False

                if not submodule_mapping:
                    submodule_mapping = SubmoduleMapping.objects.create()
                    submodule.mapping = submodule_mapping
                    submodule.save()
                    created = True

                if created:
                    self.log_addition(submodule_mapping)

            if skip_saving:
                group_exists = False
                if submodule is not None:
                    group_exists = SubmoduleRequiredGroup.objects.filter(
                        submodule=submodule,
                        required_suffix=suffix,
                        required_nested_suffix=suffix_2,
                        required_recall_period=recall_period,
                    ).exists()

                if not group_exists:
                    self.log_change(
                        SubmoduleRequiredGroup,
                        f"{submodule_name}-{suffix_name}-{suffix_2_name}-{recall_period_name}",
                        create=True,
                    )
            else:
                group_mapping, created = SubmoduleRequiredGroup.objects.get_or_create(
                    submodule=submodule,
                    required_suffix=suffix,
                    required_nested_suffix=suffix_2,
                    required_recall_period=recall_period,
                )
                self.log_addition(group_mapping)

                if group_mapping and created:
                    self.group_mappings.append(data)

        return self.group_mappings
