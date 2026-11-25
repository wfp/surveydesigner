from core.forms import TranslationForm
from django import forms

from .const import ReleaseStatus
from .models import Notification, NotificationTranslation, Release, ReleaseTranslation


class ReleaseAdminForm(forms.ModelForm):
    class Meta:
        model = Release
        fields = "__all__"
        labels = {"title": "Title (English)", "body": "Body (English, HTML)"}
        widgets = {
            "title": forms.Textarea(attrs={"rows": 2, "cols": 70}),
            "body": forms.Textarea(attrs={"rows": 10, "cols": 90}),
        }


class NotificationAdminForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = "__all__"
        labels = {
            "title": "Title (English)",
            "abstract": "Abstract (English)",
            "body": "Body (English, HTML)",
        }
        help_texts = {
            "release": (
                "Leave blank for a standalone notification. Publishing a release "
                "automatically creates its linked draft notification; edit that draft "
                "to prepare the announcement."
            )
        }
        widgets = {
            "title": forms.Textarea(attrs={"rows": 2, "cols": 70}),
            "abstract": forms.Textarea(attrs={"rows": 3, "cols": 70}),
            "body": forms.Textarea(attrs={"rows": 10, "cols": 90}),
        }

    def clean_release(self):
        release = self.cleaned_data.get("release")
        if release and release.status != ReleaseStatus.PUBLISHED:
            raise forms.ValidationError(
                "Publish the release first, then edit the linked draft notification "
                "created automatically. Leave this field blank to save a standalone "
                "notification instead.",
                code="release_not_published",
            )
        return release


class ReleaseTranslationAdminForm(TranslationForm):
    class Meta(TranslationForm.Meta):
        model = ReleaseTranslation
        labels = {"label": "Body (HTML)"}
        widgets = {
            **TranslationForm.Meta.widgets,
            "title": forms.Textarea(attrs={"rows": 2, "cols": 30}),
            "label": forms.Textarea(attrs={"rows": 5, "cols": 55}),
        }


class NotificationTranslationAdminForm(TranslationForm):
    class Meta(TranslationForm.Meta):
        model = NotificationTranslation
        labels = {"label": "Body (HTML)"}
        widgets = {
            **TranslationForm.Meta.widgets,
            "title": forms.Textarea(attrs={"rows": 2, "cols": 30}),
            "abstract": forms.Textarea(attrs={"rows": 3, "cols": 30}),
            "label": forms.Textarea(attrs={"rows": 5, "cols": 55}),
        }
