from django.conf import settings
from openpyxl import load_workbook
from organization.models import Organization
from questions.services.questions_import.choices import ChoicesImport
from questions.services.questions_import.indicators import IndicatorsImport
from questions.services.questions_import.questions import QuestionsImport
from questions.services.questions_import.recall_period import RecallPeriodImport
from questions.services.questions_import.submodule_required_group import (
    SubmoduleRequiredGroupImport,
)
from questions.services.questions_import.suffixes import SuffixesImport


class DataImport:
    def __init__(
        self,
        xls_file,
        user,
        organizations,
        change_request=None,
    ):
        if organizations is None:
            organizations = Organization.objects.none()
        self.xls_file = xls_file
        self.user = user
        self.change_request = change_request
        self.languages_dict = dict(settings.LANGUAGES)

        self.wb = load_workbook(self.xls_file)
        self.questions_sheet = self.wb["survey"]
        self.choices_sheet = self.wb["choices"]
        self.suffixes_sheet = self.wb["suffixes"]
        self.recall_periods_sheet = self.wb["recall_periods"]
        self.required_groups_sheet = self.wb["required_groups"]
        self.indicators_sheet = self.wb["indicators"]

        self.recall_periods_import = RecallPeriodImport(
            self.recall_periods_sheet,
            user,
            change_request=self.change_request,
            organizations=organizations,
        )
        self.choices_import = ChoicesImport(
            self.choices_sheet,
            self.languages_dict,
            user,
            change_request=self.change_request,
        )
        self.suffixes_import = SuffixesImport(
            self.suffixes_sheet, user, change_request=self.change_request
        )
        self.questions_import = QuestionsImport(
            self.questions_sheet,
            self.languages_dict,
            user,
            change_request=self.change_request,
            organizations=organizations,
        )
        self.required_groups_import = SubmoduleRequiredGroupImport(
            self.required_groups_sheet,
            user,
            change_request=self.change_request,
        )
        self.indicators_import = IndicatorsImport(
            self.indicators_sheet,
            user,
            change_request=self.change_request,
        )

    def process(self):
        self.recall_periods_import.process()
        self.choices_import.process()
        processed_choice_names = self.choices_import.get_processed_names()

        self.suffixes_import.process(processed_choice_names)
        processed_suffix_names = self.suffixes_import.get_processed_names()

        self.questions_import.process(
            available_spreadsheet_choices=processed_choice_names,
            available_spreadsheet_suffixes=processed_suffix_names,
        )
        processed_questions = self.questions_import.get_processed_names()
        self.required_groups_import.process()
        self.indicators_import.process(processed_questions)

    def is_valid(self):
        return (
            self.recall_periods_import.is_valid()
            and self.choices_import.is_valid()
            and self.suffixes_import.is_valid()
            and self.questions_import.is_valid()
            and self.required_groups_import.is_valid()
            and self.indicators_import.is_valid()
        )

    @property
    def existing_questions(self):
        return self.questions_import.existing_questions

    def get_errors(self):
        errors = {}
        if (
            self.recall_periods_import.errors
            or self.recall_periods_import.non_form_errors
        ):
            errors["Recall Periods Spreadsheet"] = {
                "errors": self.recall_periods_import.errors,
                "non_form_errors": self.recall_periods_import.non_form_errors,
            }

        if self.choices_import.errors or self.choices_import.non_form_errors:
            errors["Choices Spreadsheet"] = {
                "errors": self.choices_import.errors,
                "non_form_errors": self.choices_import.non_form_errors,
            }

        if self.suffixes_import.errors or self.suffixes_import.non_form_errors:
            errors["Suffixes Spreadsheet"] = {
                "errors": self.suffixes_import.errors,
                "non_form_errors": self.suffixes_import.non_form_errors,
            }

        if self.questions_import.errors or self.questions_import.non_form_errors:
            errors["Questions Spreadsheet"] = {
                "errors": self.questions_import.errors,
                "non_form_errors": self.questions_import.non_form_errors,
            }

        if (
            self.required_groups_import.errors
            or self.required_groups_import.non_form_errors
        ):
            errors["Required Groups Spreadsheet"] = {
                "errors": self.questions_import.errors,
                "non_form_errors": self.questions_import.non_form_errors,
            }

        if self.indicators_import.errors or self.indicators_import.non_form_errors:
            errors["Indicators Spreadsheet"] = {
                "errors": self.indicators_import.errors,
                "non_form_errors": self.indicators_import.non_form_errors,
            }

        return errors

    def get_updates(self):
        updates = {}
        to_create_key = "To Create"
        to_update_key = "To Update"

        if (
            self.recall_periods_import.to_be_created
            or self.recall_periods_import.to_be_updated
        ):
            updates["Recall Periods Spreadsheet"] = {
                to_create_key: dict(self.recall_periods_import.to_be_created),
                to_update_key: dict(self.recall_periods_import.to_be_updated),
            }

        if self.choices_import.to_be_created or self.choices_import.to_be_updated:
            updates["Choices Spreadsheet"] = {
                to_create_key: dict(self.choices_import.to_be_created),
                to_update_key: dict(self.choices_import.to_be_updated),
            }

        if self.suffixes_import.to_be_created or self.suffixes_import.to_be_updated:
            updates["Suffixes Spreadsheet"] = {
                to_create_key: dict(self.suffixes_import.to_be_created),
                to_update_key: dict(self.suffixes_import.to_be_updated),
            }

        if self.questions_import.to_be_created or self.questions_import.to_be_updated:
            updates["Questions Spreadsheet"] = {
                to_create_key: dict(self.questions_import.to_be_created),
                to_update_key: dict(self.questions_import.to_be_updated),
            }

        if (
            self.required_groups_import.to_be_created
            or self.required_groups_import.to_be_updated
        ):
            updates["Required Groups Spreadsheet"] = {
                to_create_key: dict(self.required_groups_import.to_be_created),
                to_update_key: dict(self.required_groups_import.to_be_updated),
            }

        if self.indicators_import.to_be_created or self.indicators_import.to_be_updated:
            updates["Indicators Spreadsheet"] = {
                to_create_key: dict(self.indicators_import.to_be_created),
                to_update_key: dict(self.indicators_import.to_be_updated),
            }

        return updates

    def create(self, skip_saving=False):
        created_recall_periods = self.recall_periods_import.create(skip_saving)
        created_choices = self.choices_import.create(skip_saving)
        created_suffixes = self.suffixes_import.create(created_choices, skip_saving)
        created = self.questions_import.create(
            created_choices, created_suffixes, skip_saving
        )
        created_groups = self.required_groups_import.create(skip_saving)
        created_indicators = self.indicators_import.create(skip_saving)
        return (
            created,
            created_choices,
            created_suffixes,
            created_recall_periods,
            created_groups,
            created_indicators,
        )
