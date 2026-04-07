from dal import autocomplete
from django.conf import settings
from django import forms


class TranslationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language_field = self.fields.get("language")
        if language_field:
            choices = [
                language for language in settings.LANGUAGES if language[0] != "en"
            ]
            instance = getattr(self, "instance", None)
            if (
                instance
                and instance.pk
                and getattr(instance, "language", None) == "en"
            ):
                choices = [
                    language for language in settings.LANGUAGES if language[0] == "en"
                ] + choices
            language_field.choices = choices

    def clean_language(self):
        language = self.cleaned_data["language"]
        instance = getattr(self, "instance", None)
        if (
            language == "en"
            and not (
                instance and instance.pk and getattr(instance, "language", None) == "en"
            )
        ):
            raise forms.ValidationError(
                "English is managed by the main Label (en) and Hint (en) fields."
            )
        return language

    class Meta:
        fields = "__all__"
        widgets = {"language": autocomplete.Select2(url="v1:language-autocomplete")}
