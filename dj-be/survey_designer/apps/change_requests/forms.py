import os

from change_requests.const import StatusType
from change_requests.models import ChangeRequest
from django import forms
from django.core.exceptions import ValidationError
from organization.models import Organization


class ChangeRequestAdminForm(forms.ModelForm):
    def clean_status(self):
        status = self.cleaned_data["status"]
        if self.instance and self.instance.id:
            if self.instance.is_approved and status != StatusType.APPROVED:
                raise ValidationError(
                    "You cannot change the status. Change request has been approved."
                )
            elif self.instance.is_rejected and status != StatusType.REJECTED:
                raise ValidationError(
                    "You cannot change the status. Change request has been rejected."
                )
        return status


class ChangeRequestForm(forms.ModelForm):
    organizations = forms.ModelMultipleChoiceField(queryset=Organization.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organizations"].queryset = Organization.objects.all()

    class Meta:
        model = ChangeRequest
        fields = ("file", "description", "organizations")

    def clean_file(self):
        file = self.cleaned_data["file"]
        filename, file_extension = os.path.splitext(file.name)
        if file_extension not in (".xls", ".xlsx"):
            self.add_error("file", "Only XLS or XLSX files are allowed.")
        return file


class ApproveChangeRequestForm(forms.ModelForm):
    class Meta:
        model = ChangeRequest
        fields = ("response",)
