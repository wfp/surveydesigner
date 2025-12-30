from dal import autocomplete
from django import forms


class TranslationForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        widgets = {"language": autocomplete.Select2(url="v1:language-autocomplete")}
