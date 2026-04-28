import enum
from collections import defaultdict

from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from questions.models import BaseQuestion, SubQuestion

ENGLISH_LANGUAGE_CODE = "en"


class QuestionImportException(Exception):
    pass


class BaseImport:
    def __init__(self, user, change_request=None):
        self.user = user
        self.change_request = change_request
        self.errors = {}
        self.non_form_errors = []
        self.user_tracking_kwargs = {
            "created_by": self.user,
            "updated_by": self.user,
        }

        self.to_be_created = defaultdict(list)
        self.to_be_updated = defaultdict(list)

    def get_value(self, row, key: enum.Enum):
        value = row[key.value].value
        if value is None:
            return

        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def is_valid(self):
        return not self.errors and not self.non_form_errors

    def log_addition(self, obj, message=""):
        content_type_id = ContentType.objects.get_for_model(
            obj, for_concrete_model=False
        ).pk

        default_message = "Added using Bulk Upload"

        if self.change_request:
            requested_by_msg = ""
            if self.change_request.created_by:
                requested_by_msg = (
                    f" | Requested by: {self.change_request.created_by.email}"
                )

            default_message = f"{default_message} | Change Request ID: {self.change_request.id}{requested_by_msg}"

        return LogEntry.objects.log_action(
            user_id=self.user.pk,
            content_type_id=content_type_id,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=ADDITION,
            change_message=message if message else default_message,
        )

    def log_change(self, model, name, create):
        if model == BaseQuestion:
            model_name = "Question"
        elif model == SubQuestion:
            model_name = "Sub Question"
        else:
            model_name = model._meta.verbose_name.title()

        changes = self.to_be_created if create else self.to_be_updated
        if name not in changes[model_name]:
            changes[model_name].append(name)
