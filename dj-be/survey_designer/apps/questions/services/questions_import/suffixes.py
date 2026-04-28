import enum
from collections import defaultdict

from questions.forms import SuffixImportRowForm
from questions.models import ChoiceGroup, Suffix
from questions.services.questions_import.base import BaseImport, QuestionImportException


class SuffixesImport(BaseImport):
    columns_mapping = {
        "name": "NAME",
        "description": "DESCRIPTION",
        "type": "TYPE",
        "choicelist": "CHOICE_LIST",
        "suffix": "SUFFIX",  # for nested suffixes
    }
    form = SuffixImportRowForm

    def __init__(self, suffixes_sheet, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.work_sheet = suffixes_sheet
        self.columns = None

        self.cleaned_data = []

        self.processed_names = set()
        self.processed_names_with_nested_suffixes = {}
        self.choice_lists_to_validate = set()
        self.nested_suffixes_to_validate = set()
        self.suffixes_dict = {}
        self.nested_suffixes_to_add = defaultdict(list)

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
                "Incorrect suffixes spreadsheet. Missing columns."
            )

        self.columns = enum.Enum("COLUMNS", columns)

    def _check_nested_suffixes(self):
        missing_nested_suffixes = self.nested_suffixes_to_validate.difference(
            self.processed_names
        )

        self.suffixes_dict = {
            sfx.name: sfx
            for sfx in Suffix.objects.filter(name__in=missing_nested_suffixes)
        }

        db_suffixes_names = set(self.suffixes_dict.keys())

        missing_nested_suffixes = missing_nested_suffixes.difference(db_suffixes_names)

        if missing_nested_suffixes:
            self.non_form_errors.append(
                f"Missing suffixes used in suffix column: {', '.join(missing_nested_suffixes)}"
            )

    def _check_choices(self, available_spreadsheet_choices: set):
        missing_choices = set()
        for choice_name in self.choice_lists_to_validate:
            if choice_name not in available_spreadsheet_choices:
                missing_choices.add(choice_name)

        if missing_choices:
            existing_choices = set(
                ChoiceGroup.objects.filter(name__in=missing_choices).values_list(
                    "name", flat=True
                )
            )
            missing_choices = missing_choices.difference(existing_choices)

            if missing_choices:
                self.non_form_errors.append(
                    f"Choices | Missing choices: {', '.join(missing_choices)}"
                )

    def populate_data_for_validation(self, cleaned_data):
        name = cleaned_data.get("name")
        choice_list = cleaned_data.get("choice_list")
        nested_suffixes = cleaned_data.get("nested_suffixes", [])

        if name:
            self.processed_names.add(name)

        if choice_list:
            self.choice_lists_to_validate.add(choice_list)

        if nested_suffixes:
            self.nested_suffixes_to_validate.update(nested_suffixes)

        self.processed_names_with_nested_suffixes[name] = set(nested_suffixes)

    def get_row_form(self, row):
        data = {
            "name": self.get_value(row, self.columns.NAME),
            "description": self.get_value(row, self.columns.DESCRIPTION),
            "type": self.get_value(row, self.columns.TYPE),
            "choice_list": self.get_value(row, self.columns.CHOICE_LIST),
            "nested_suffixes": self.get_value(row, self.columns.SUFFIX),
        }
        return self.form(data=data)

    def process(self, available_spreadsheet_choices: set):
        try:
            self.validate_and_set_columns()
        except QuestionImportException as error:
            self.non_form_errors.append(str(error))
            return

        for counter, row in enumerate(self.work_sheet.iter_rows(min_row=2), 2):
            if not self.get_value(row, self.columns.NAME):
                continue

            form = self.get_row_form(row)
            if form.is_valid():
                self.cleaned_data.append(form.cleaned_data)
            else:
                self.errors[counter] = form.errors

            self.populate_data_for_validation(form.cleaned_data)

        self._check_nested_suffixes()
        self._check_choices(available_spreadsheet_choices)

    def get_choice_list(self, name, created_choices):
        if name:
            return created_choices.get(name) or ChoiceGroup.objects.get(
                name__iexact=name
            )
        return

    def get_processed_names(self) -> dict:
        return self.processed_names_with_nested_suffixes

    def _suffix_has_changes(self, suffix, data):
        existing_choice_list = suffix.choices.name.casefold() if suffix.choices else ""
        new_choice_list = (data.get("choice_list") or "").casefold()
        existing_nested_suffixes = {
            name.casefold()
            for name in suffix.nested_suffixes.values_list("name", flat=True)
        }
        new_nested_suffixes = {
            nested_suffix.casefold()
            for nested_suffix in (data.get("nested_suffixes") or [])
        }

        return (
            (suffix.description or "") != (data.get("description") or "")
            or suffix.type != data["type"]
            or existing_choice_list != new_choice_list
            or existing_nested_suffixes != new_nested_suffixes
        )

    def create(self, created_choices: dict, skip_saving=False):
        suffixes_to_process = {}

        for data in self.cleaned_data:
            name = data["name"]

            if skip_saving:
                suffix = Suffix.objects.filter(name__iexact=name).first()
                if not suffix:
                    self.log_change(Suffix, name, create=True)
                elif self._suffix_has_changes(suffix, data):
                    self.log_change(Suffix, name, create=False)
            else:
                suffix, created = self.permissions_based_method(
                    name=data["name"],
                    defaults={
                        "description": data.get("description", ""),
                        "type": data["type"],
                        "choices": self.get_choice_list(
                            data["choice_list"], created_choices
                        ),
                        **self.user_tracking_kwargs,
                    },
                )

                self.log_addition(suffix)

                nested_suffixes = data.get("nested_suffixes")
                if nested_suffixes:
                    suffixes_to_process[suffix] = nested_suffixes

            if suffix:
                self.suffixes_dict[name] = suffix

        if not skip_saving:
            for suffix, nested_suffixes in suffixes_to_process.items():
                sfx_instances = [
                    self.suffixes_dict[sfx_name] for sfx_name in nested_suffixes
                ]
                suffix.nested_suffixes.set(sfx_instances)

        return self.suffixes_dict

    @property
    def permissions_based_method(self):
        if self.user.is_global_admins_member or self.user.is_superuser:
            return Suffix.objects.update_or_create
        return Suffix.objects.get_or_create
