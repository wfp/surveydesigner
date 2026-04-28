import enum
from collections import defaultdict

from questions.models import Choice, ChoiceGroup, ChoiceTranslation
from questions.services.questions_import.base import (
    ENGLISH_LANGUAGE_CODE,
    BaseImport,
    QuestionImportException,
)


class ChoicesImport(BaseImport):
    columns_mapping = {
        # "<value in spreadsheet>": "<enum attribute>"
        "choice_list": "CHOICE_LIST",
        "name": "NAME",
    }

    def __init__(self, choices_sheet, languages_dict, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.work_sheet = choices_sheet
        self.languages_dict = languages_dict
        self.choices = {}  # {ChoiceGroup.name: ChoiceGroup instance}
        self.columns = None
        self.language_columns = None

        self.cleaned_data = defaultdict(lambda: dict(choices=[]))

    def validate_and_set_columns(self):
        columns = []
        language_columns = []

        language_label_prefix = "label::"
        inv_languages_dict = {v: k for k, v in self.languages_dict.items()}
        for counter, cell in enumerate(self.work_sheet[1]):
            if not cell.value:
                continue
            key = self.columns_mapping.get(cell.value.lower())
            if key:
                columns.append((key, counter))
                continue

            if language_label_prefix in cell.value:
                parts = (
                    cell.value.replace(language_label_prefix, "")
                    .replace(")", "")
                    .split("(")
                )
                parts.append("")
                language_display, language_code, *rest = parts
                language_display = language_display.strip()
                language_code = language_code.strip()

                code = self.languages_dict.get(language_code) or inv_languages_dict.get(
                    language_display
                )

                if not code:
                    raise QuestionImportException(
                        f"Language not found for column: {cell.value}"
                    )

                language_columns.append((language_code or code, counter))

        if len(self.columns_mapping) != len(columns):
            raise QuestionImportException(
                "Incorrect choices spreadsheet. Missing columns."
            )

        if not language_columns:
            raise QuestionImportException(
                "Question translation column missing or not correct."
            )

        self.columns = enum.Enum("COLUMNS", columns)
        self.language_columns = enum.Enum("LANGUAGE_COLUMNS", language_columns)

    def process(self):
        try:
            self.validate_and_set_columns()
        except QuestionImportException as error:
            self.non_form_errors.append(str(error))

        choice_option_names = defaultdict(set)

        for counter, row in enumerate(self.work_sheet.iter_rows(min_row=2), 2):
            choice_languages = {}
            choice_list_value = self.get_value(row, self.columns.CHOICE_LIST)
            if not choice_list_value:
                continue

            name = self.get_value(row, self.columns.NAME)
            label = self.get_value(row, self.language_columns[ENGLISH_LANGUAGE_CODE])

            if name in (None, ""):
                self.non_form_errors.append(
                    f"Choices | Row: {counter} | Name is missing."
                )

            if name in choice_option_names[choice_list_value]:
                self.non_form_errors.append(
                    f"Choices | Row: {counter} | Name ({name}) is repeated for {choice_list_value}."
                )

            choice_option_names[choice_list_value].add(name)

            if not label:
                self.non_form_errors.append(
                    f"Choices | Row: {counter} | English label is required."
                )

            for language in self.language_columns:
                if language.name == ENGLISH_LANGUAGE_CODE:
                    continue
                translation = self.get_value(row, language)
                if translation:
                    choice_languages[language.name] = translation

            self.cleaned_data[choice_list_value]["choices"].append(
                {"name": name, "label": label, "languages": choice_languages}
            )

    def get_processed_names(self) -> set:
        return set(self.cleaned_data.keys())

    def _choice_group_has_changes(self, choice_group, choices_data):
        existing_choices = {
            choice.name.casefold(): choice
            for choice in choice_group.choices.prefetch_related("translations").all()
        }

        for idx, choice_data in enumerate(choices_data, start=1):
            existing_choice = existing_choices.get(choice_data["name"].casefold())
            if existing_choice is None:
                return True

            if existing_choice.label != choice_data["label"]:
                return True

            if getattr(existing_choice, "order", 0) in (None, 0):
                return True

            existing_translations = {
                translation.language: translation.label
                for translation in existing_choice.translations.all()
            }
            for language_name, translation in choice_data["languages"].items():
                if existing_translations.get(language_name) != translation:
                    return True

        return False

    def create(self, skip_saving=False):
        """
        Create/update ChoiceGroups, Choices, and ChoiceTranslations from cleaned_data.
        For NEW choices, set `order` from the row index (1-based) within each group.
        If an existing choice has order 0/None, also set it to the row index.
        Existing non-zero `order` values are NOT changed.
        """
        choices = {}

        for name_key, c_data in self.cleaned_data.items():
            if skip_saving:
                choice_group = ChoiceGroup.objects.filter(name__iexact=name_key).first()
                if not choice_group:
                    self.log_change(ChoiceGroup, name_key, create=True)
                elif self._choice_group_has_changes(choice_group, c_data["choices"]):
                    self.log_change(ChoiceGroup, name_key, create=False)
            else:
                choice_group, created_group = self.permissions_based_method(
                    name=name_key, defaults={**self.user_tracking_kwargs}
                )
                self.log_addition(choice_group)

                # Use the spreadsheet row order (1-based) to propose `order`
                for idx, choices_data in enumerate(c_data["choices"], start=1):
                    choice_name = choices_data["name"]
                    label = choices_data["label"]
                    languages = choices_data["languages"]

                    choice, created_choice = Choice.objects.update_or_create(
                        choice_group=choice_group,
                        name=choice_name,
                        defaults={
                            "label": label,
                            **self.user_tracking_kwargs,
                        },
                    )
                    self.log_addition(choice)

                    # Only set/repair `order` on fresh rows or "unset" (0/None) orders
                    needs_order = created_choice or getattr(choice, "order", 0) in (
                        None,
                        0,
                    )
                    if needs_order:
                        choice.order = idx
                        choice.save(update_fields=["order"])

                    # Translations
                    for lang_name, translation in languages.items():
                        c_translation, _ = ChoiceTranslation.objects.update_or_create(
                            choice=choice,
                            language=lang_name,
                            defaults={
                                "label": translation,
                                **self.user_tracking_kwargs,
                            },
                        )
                        self.log_addition(c_translation)

            if choice_group:
                choices[name_key] = choice_group

        return choices

    @property
    def permissions_based_method(self):
        if self.user.is_global_admins_member or self.user.is_superuser:
            return ChoiceGroup.objects.update_or_create
        return ChoiceGroup.objects.get_or_create
