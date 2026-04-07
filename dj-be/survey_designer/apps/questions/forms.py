import os
from datetime import datetime

from core.validators import validate_name, validate_names
from dal import autocomplete
from django import forms
from django.conf import settings
from django.forms import Form, ModelForm
from django.forms.models import BaseInlineFormSet
from modules.models import Indicator, Submodule
from openpyxl import load_workbook
from organization.models import Organization
from questions.const import (
    LogicalOperatorType,
    OperatorType,
    QuestionType,
    ReferenceQuestionType,
)
from questions.models import (
    BaseQuestion,
    Calculation,
    ChoiceGroupFile,
    RepeatSection,
    RootQuestion,
    SubQuestion,
    Suffix,
)


class SubQuestionAdminModelForm(ModelForm):
    repeat_sections = forms.ModelMultipleChoiceField(
        queryset=RepeatSection.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url="v1:repeat-section-autocomplete"),
    )
    indicators = forms.ModelMultipleChoiceField(
        queryset=Indicator.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url="v1:indicator-autocomplete"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("suffix", "suffix_2"):
            suffix_field = self.fields.get(field_name)
            if suffix_field:
                suffix_field.queryset = suffix_field.queryset.order_by("name")

        try:
            self.fields["constraint"].widget.attrs["class"] = "sub_question_constraint"
            self.fields["constraint_message"].widget.attrs[
                "class"
            ] = "sub_question_constraint_message"
            self.fields["relevant"].widget.attrs["class"] = "sub_question_relevant"
            self.fields["choice_filter"].widget.attrs[
                "class"
            ] = "sub_question_choice_filter"
            self.fields["calculation"].widget.attrs[
                "class"
            ] = "sub_question_calculation"
        except KeyError:
            # catching for Read Only group
            pass

        self.fields["repeat_sections"].widget.attrs[
            "class"
        ] = "sub_question_repeat_sections"

        if self.instance and self.instance.id:
            initial_repeats = RepeatSection.objects.filter(
                questions=self.instance.root_question.base_question
            )
            self.fields["repeat_sections"].queryset = initial_repeats
            self.fields["repeat_sections"].initial = initial_repeats

            initial_indicators = Indicator.objects.filter(
                questions=self.instance.base_question
            )
            self.fields["indicators"].queryset = initial_indicators
            self.fields["indicators"].initial = initial_indicators
        if self.data:
            self.fields["repeat_sections"].queryset = RepeatSection.objects.all()
            self.fields["indicators"].queryset = Indicator.objects.all()

    def check_question_names(self, field_name, field_value, error_message):
        names = BaseQuestion.get_question_names(field_value)
        # If there are no ${...} in the string, we consider it valid and return early
        if not names:
            return
        base_questions = BaseQuestion.get_base_questions(names)
        if not base_questions.exists():
            self.add_error(
                field_name,
                f"Invalid {error_message} - Questions not found: {', '.join(names)}",
            )

    def clean(self):
        super().clean()
        suffix = self.cleaned_data.get("suffix")
        suffix_2 = self.cleaned_data.get("suffix_2")
        recall_period = self.cleaned_data.get("recall_period")
        constraint = self.cleaned_data.get("constraint")
        relevant = self.cleaned_data.get("relevant")
        choice_filter = self.cleaned_data.get("choice_filter")
        calculation = self.cleaned_data.get("calculation")

        if not (suffix or recall_period):
            self.add_error("", "Suffix or Recall Period have to be selected.")

        if suffix_2 and not suffix:
            self.add_error("", "When Suffix 2 is selected Suffix is required.")

        if suffix and suffix_2 and suffix == suffix_2:
            self.add_error("", "Suffix cannot be the same as Suffix 2.")

        if constraint:
            self.check_question_names("constraint", constraint, "constraint")

        if relevant:
            self.check_question_names("relevant", relevant, "relevant")

        if choice_filter:
            self.check_question_names("choice_filter", choice_filter, "choice filter")

        if calculation:
            self.check_question_names("calculation", calculation, "calculation")
        return self.cleaned_data


class SuffixAdminForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices_field = self.fields.get("choices")
        if choices_field:
            choices_field.queryset = choices_field.queryset.order_by("name")

    def clean_nested_suffixes(self):
        data = self.cleaned_data["nested_suffixes"]
        if self.instance in data:
            self.add_error("nested_suffixes", "Suffix cannot be related to itself.")
        return data


class CalculationAdminModelForm(ModelForm):
    def clean_calculation(self):
        calculation = self.cleaned_data["calculation"]

        question_names = Calculation.get_question_names(calculation)
        base_questions = Calculation.get_base_questions(question_names)

        if not question_names:
            message = f"No questions found in calculation: {calculation}"
            self.add_error("calculation", message)

        missing_questions = [
            question_name
            for question_name in question_names
            if question_name not in {question.name for question in base_questions}
        ]
        if missing_questions:
            message = f"Questions not found: {', '.join(missing_questions)}"
            self.add_error("calculation", message)
        return calculation


class RootQuestionAdminModelForm(ModelForm):
    repeat_sections = forms.ModelMultipleChoiceField(
        queryset=RepeatSection.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url="v1:repeat-section-autocomplete"),
    )
    indicators = forms.ModelMultipleChoiceField(
        queryset=Indicator.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url="v1:indicator-autocomplete"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices_field = self.fields.get("choices")
        if choices_field:
            choices_field.queryset = choices_field.queryset.order_by("name")

        choices_file_field = self.fields.get("choices_file")
        if choices_file_field:
            choices_file_field.queryset = choices_file_field.queryset.order_by("name")

        # Dynamically set required based on question type
        type_value = None
        if self.data:
            type_value = self.data.get("type")
        elif self.instance and self.instance.type:
            type_value = self.instance.type

        if type_value:
            if type_value in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE):
                if choices_field:
                    choices_field.required = True
                if choices_file_field:
                    choices_file_field.required = False
            elif type_value in (
                QuestionType.SELECT_ONE_FROM_FILE,
                QuestionType.SELECT_MULTIPLE_FROM_FILE,
            ):
                if choices_file_field:
                    choices_file_field.required = True
                if choices_field:
                    choices_field.required = False
            else:
                if choices_field:
                    choices_field.required = False
                if choices_file_field:
                    choices_file_field.required = False

        if self.instance and self.instance.id:
            initial_repeats = RepeatSection.objects.filter(
                questions=self.instance.base_question
            )
            self.fields["repeat_sections"].queryset = initial_repeats
            self.fields["repeat_sections"].initial = initial_repeats

            initial_indicators = Indicator.objects.filter(
                questions=self.instance.base_question
            )
            self.fields["indicators"].queryset = initial_indicators
            self.fields["indicators"].initial = initial_indicators

        if self.data:
            self.fields["repeat_sections"].queryset = RepeatSection.objects.all()
            self.fields["indicators"].queryset = Indicator.objects.all()

        if self.fields.get("submodule"):
            self.fields["submodule"].queryset = Submodule.objects.visible_for_user(
                self.user
            )

    def check_question_names(self, field_name, field_value, error_message):
        names = BaseQuestion.get_question_names(field_value)
        # If there are no ${...} in the string, we consider it valid and return early
        if not names:
            return
        base_questions = BaseQuestion.get_base_questions(names)
        if not base_questions.exists():
            self.add_error(
                field_name,
                f"Invalid {error_message} - Questions not found: {', '.join(names)}",
            )

    def clean(self):
        super().clean()
        type_ = self.cleaned_data.get("type")
        choices = self.cleaned_data.get("choices")
        choices_file = self.cleaned_data.get("choices_file")
        constraint = self.cleaned_data.get("constraint")
        relevant = self.cleaned_data.get("relevant")
        choice_filter = self.cleaned_data.get("choice_filter")
        calculation = self.cleaned_data.get("calculation")

        if type_:
            if type_ in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE):
                if not choices:
                    self.add_error("choices", "This field is required.")
                if choices_file:
                    self.add_error(
                        "choices_file",
                        "Cannot set both 'choices' and 'choices_file'. Use 'choices' for regular question types.",
                    )
            elif type_ in (
                QuestionType.SELECT_ONE_FROM_FILE,
                QuestionType.SELECT_MULTIPLE_FROM_FILE,
            ):
                if not choices_file:
                    self.add_error("choices_file", "This field is required.")
                if choices:
                    self.add_error(
                        "choices",
                        "Cannot set both 'choices' and 'choices_file'. Use 'choices_file' for file-based question types.",
                    )

        if constraint:
            self.check_question_names("constraint", constraint, "constraint")

        if relevant:
            self.check_question_names("relevant", relevant, "relevant")

        if choice_filter:
            self.check_question_names("choice_filter", choice_filter, "choice filter")

        if calculation:
            self.check_question_names("calculation", calculation, "calculation")
        return self.cleaned_data


class NestedSuffixForm(ModelForm):
    suffixes = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nested_suffixes"].required = True

    def clean(self):
        super().clean()
        suffix_names = self.cleaned_data["suffixes"]

        if not suffix_names:
            self.add_error("", "Suffixes not provided.")

        suffix_names = suffix_names.split(",")

        self.cleaned_data["suffixes"] = Suffix.objects.filter(name__in=suffix_names)
        return self.cleaned_data

    def save(self, commit=True):
        suffixes = self.cleaned_data["suffixes"]
        nested_suffixes = self.cleaned_data["nested_suffixes"]
        for suffix in suffixes:
            suffix.nested_suffixes.add(*nested_suffixes)

        nested_suffix_names = ", ".join(sfx.name for sfx in nested_suffixes)

        return suffixes, nested_suffix_names


class SubQuestionProxyForm(ModelForm):
    root_question_ids = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean(self):
        super().clean()
        root_question_ids = self.cleaned_data["root_question_ids"]
        suffix = self.cleaned_data["suffix"]
        suffix_2 = self.cleaned_data["suffix_2"]
        recall_period = self.cleaned_data["recall_period"]

        if not (suffix or recall_period):
            self.add_error("", "Suffix or Recall Period have to be selected.")

        if suffix_2 and not suffix:
            self.add_error("", "When Suffix 2 is selected Suffix is required.")

        if suffix and suffix_2 and suffix == suffix_2:
            self.add_error("", "Suffix cannot be the same as Suffix 2.")

        suffix_name = suffix.name if suffix else ""
        suffix_2_name = suffix_2.name if suffix_2 else ""
        recall_period_name = recall_period.name if recall_period else ""

        partial_name = f"{suffix_name}{suffix_2_name}{recall_period_name}"

        if not root_question_ids:
            self.add_error("", "Root questions were not selected.")

        root_question_ids = root_question_ids.split(",")
        root_questions = RootQuestion.objects.filter(id__in=root_question_ids)

        for root_question in root_questions:
            full_name = f"{root_question.name}{partial_name}"
            if SubQuestion.objects.filter(name=full_name).exists():
                self.add_error(
                    "", f"Question with this name already exists ({full_name})"
                )

        self.cleaned_data["root_questions"] = root_questions
        return self.cleaned_data

    def save(self, commit=True):
        sub_questions_created = []
        root_questions = self.cleaned_data["root_questions"]
        suffix = self.cleaned_data["suffix"]
        suffix_2 = self.cleaned_data["suffix_2"]
        recall_period = self.cleaned_data["recall_period"]
        label = self.cleaned_data["label"]

        for root_question in root_questions:
            root_question.updated_by = self.user
            root_question.save()
            sub_question = SubQuestion.objects.create(
                root_question=root_question,
                suffix=suffix,
                suffix_2=suffix_2,
                recall_period=recall_period,
                label=label,
            )

            sub_questions_created.append(sub_question)

        return sub_questions_created, root_questions


class SubQuestionProxyTranslationFormset(BaseInlineFormSet):
    def __init__(
        self,
        data=None,
        files=None,
        instance=None,
        save_as_new=False,
        prefix=None,
        queryset=None,
        **kwargs,
    ):
        self._sub_questions, _ = (
            instance if isinstance(instance, tuple) else (None, None)
        )
        self._created_translations = {}
        super().__init__(
            data=data,
            files=files,
            instance=None,
            save_as_new=save_as_new,
            prefix=prefix,
            queryset=queryset,
            **kwargs,
        )


class QuestionValidationForm(Form):
    base_questions = forms.ModelMultipleChoiceField(
        queryset=BaseQuestion.objects.none(), required=False
    )
    mode = forms.ChoiceField(
        choices=(("text", "Text"), ("form", "Form")),
        widget=forms.RadioSelect(),
        initial="text",
    )
    constraint = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2, "cols": 100})
    )
    constraint_message = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2, "cols": 100})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_questions = self.initial.get("base_questions")

        if self.data:
            self.base_questions_qs = BaseQuestion.objects.filter(
                id__in=self.data.getlist("base_questions")
            )
        else:
            self.base_questions_qs = base_questions

        self.fields["base_questions"].queryset = self.base_questions_qs
        self.validation_type = base_questions[0].type if base_questions else ""

    def clean(self):
        super().clean()
        base_questions = self.cleaned_data["base_questions"]
        if not base_questions:
            self.add_error("base_questions", "This field is required.")
        else:
            types = set()
            counter = 0

            for question in base_questions:
                counter += 1
                types.add(question.type)

            if len(types) != counter:
                self.add_error(
                    "base_questions", "Questions have to have the same types."
                )

        mode = self.cleaned_data["mode"]
        if mode == "text" and not self.cleaned_data["constraint"]:
            self.add_error("constraint", "This field is required.")

        return self.cleaned_data


class QuestionConstraintForm(Form):
    question_value = forms.CharField(max_length=255, initial=".", required=False)
    operator = forms.ChoiceField(choices=OperatorType.choices, required=False)
    value = forms.CharField(max_length=255, required=False)
    logical_operator = forms.ChoiceField(
        choices=LogicalOperatorType.choices,
        required=False,
    )
    reference_question = forms.ChoiceField(choices=ReferenceQuestionType.choices)
    question = forms.ModelChoiceField(
        queryset=BaseQuestion.objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        self.parent_form = kwargs.pop("parent_form", None)
        super().__init__(*args, **kwargs)
        self.fields["value"].widget.attrs["class"] = "value-input"
        self.fields["question"].widget.attrs["class"] = "question-select"
        self.fields["reference_question"].widget.attrs[
            "class"
        ] = "reference-question-select"

        if self.data:
            self.fields["question"].queryset = BaseQuestion.objects.filter(
                id=self.data.get("question")
            )

    def _validate_value(self, value):
        validation_type = self.parent_form.validation_type

        if validation_type == QuestionType.INTEGER and not value.isdigit():
            self.add_error(
                "value", f"Wrong value type. Allowed type: {QuestionType.INTEGER}"
            )

        if (
            validation_type == QuestionType.DECIMAL
            and not value.replace(".", "", 1).isdigit()
        ):
            self.add_error(
                "value", f"Wrong value type. Allowed type: {QuestionType.DECIMAL}"
            )

        if validation_type == QuestionType.DATE and value != "today":
            if value != "today":
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    self.add_error(
                        "value", f"Wrong value type. Allowed type: {QuestionType.DATE}"
                    )

        return value

    def clean(self):
        super().clean()
        if self.prefix[-1] != "0" and not self.cleaned_data["logical_operator"]:
            self.add_error("logical_operator", "This field is required")

        reference_question = self.cleaned_data["reference_question"]

        if (
            reference_question == ReferenceQuestionType.OTHER
            and not self.cleaned_data["question"]
        ):
            self.add_error("question", "This field is required.")

        if reference_question == ReferenceQuestionType.SELF:
            value = self.cleaned_data["value"]
            if value:
                self._validate_value(value)
            else:
                self.add_error("value", "This field is required")

        return self.cleaned_data


class QuestionConstraintTranslationForm(Form):
    language = forms.ChoiceField(choices=[("", "-----")] + settings.LANGUAGES)
    label = forms.CharField(widget=forms.Textarea(attrs={"rows": 2, "cols": 100}))


class QuestionRelevantForm(Form):
    base_questions = forms.ModelMultipleChoiceField(
        queryset=BaseQuestion.objects.none(),
        required=False,
    )
    relevant = forms.CharField(widget=forms.Textarea(attrs={"rows": 2, "cols": 100}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_questions = self.initial.get("base_questions")

        if self.data:
            self.base_questions_qs = BaseQuestion.objects.filter(
                id__in=self.data.getlist("base_questions")
            )
        else:
            self.base_questions_qs = base_questions

        self.fields["base_questions"].queryset = self.base_questions_qs


class UploadQuestionsForm(Form):
    file = forms.FileField()
    organizations = forms.ModelMultipleChoiceField(queryset=Organization.objects.all())

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        user = request.user
        if not (user.is_global_admins_member or user.is_superuser):
            self.fields["organizations"].queryset = Organization.objects.filter(
                id=user.organization.id if user.organization else None
            )
            self.fields["organizations"].initial = [user.organization]
            self.fields["organizations"].disabled = True

    def clean_file(self):
        file = self.cleaned_data["file"]
        filename, file_extension = os.path.splitext(file.name)
        if file_extension not in (".xls", ".xlsx"):
            self.add_error("file", "Only XLS or XLSX files are allowed.")
        else:
            wb = load_workbook(file)
            for sheet_name in (
                "survey",
                "choices",
                "suffixes",
                "recall_periods",
                "required_groups",
                "indicators",
            ):
                try:
                    _ = wb[sheet_name]
                except KeyError:
                    self.add_error("file", f"File is missing '{sheet_name}' sheet.")

        return file


class ChoiceGroupFileAdminModelForm(ModelForm):
    class Meta:
        model = ChoiceGroupFile
        fields = "__all__"

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get("csv_file")
        if csv_file:
            max_size = 10 * 1024 * 1024
            if csv_file.size > max_size:
                raise forms.ValidationError(
                    f"File size exceeds the maximum allowed size of 10MB. Current file size: {csv_file.size / (1024 * 1024):.2f}MB"
                )
        return csv_file


class DownloadTemplateForm(Form):
    languages = forms.MultipleChoiceField(choices=settings.LANGUAGES)


class SuffixImportRowForm(Form):
    name = forms.CharField(validators=[validate_name])
    description = forms.CharField(required=False)
    type = forms.ChoiceField(choices=QuestionType.choices)
    choice_list = forms.CharField(required=False, validators=[validate_name])
    nested_suffixes = forms.CharField(required=False)

    def clean(self):
        cd = super().clean()
        type_ = cd.get("type")
        choice_list = cd.get("choice_list")

        if type_ in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE):
            if not choice_list:
                self.add_error("choice_list", "This field is required.")
        elif choice_list:
            self.add_error(
                "choice_list", "You cannot add choice_list to that question type."
            )

        return self.cleaned_data

    def clean_nested_suffixes(self) -> set:
        cleaned_nested_suffixes = set()
        nested_suffixes = (
            self.cleaned_data.get("nested_suffixes", "").replace(",", " ").split()
        )
        if nested_suffixes:
            for sfx in nested_suffixes:
                sfx = sfx.strip()
                validate_name(sfx)
                cleaned_nested_suffixes.add(sfx)

        return cleaned_nested_suffixes


class ImportRowForm(Form):
    module_name = forms.CharField(validators=[validate_name])
    module_label = forms.CharField()
    submodule_name = forms.CharField(validators=[validate_names])
    submodule_label = forms.CharField()
    name = forms.CharField(validators=[validate_name])
    label = forms.CharField(required=False)
    choice_list = forms.CharField(required=False, validators=[validate_name])
    type = forms.ChoiceField(choices=QuestionType.extended_choices)
    relevant = forms.CharField(required=False)
    constraint = forms.CharField(required=False)
    constraint_message = forms.CharField(required=False)
    calculation = forms.CharField(required=False)
    description = forms.CharField(required=False)
    repeat = forms.CharField(required=False)
    repeat_count = forms.CharField(required=False)

    suffix_1 = forms.CharField(required=False)
    suffix_2 = forms.CharField(required=False)
    recall_period = forms.CharField(required=False)
    appearance = forms.CharField(required=False)
    parameters = forms.CharField(required=False)

    default = forms.CharField(required=False)
    disabled = forms.CharField(required=False)
    read_only = forms.CharField(required=False)
    required = forms.CharField(required=False)

    def set_available_spreadsheet_suffixes(self, available_spreadsheet_suffixes):
        setattr(self, "_available_spreadsheet_suffixes", available_spreadsheet_suffixes)

    @property
    def available_spreadsheet_suffixes(self) -> dict:
        return getattr(self, "_available_spreadsheet_suffixes")

    @property
    def is_for_sub_question(self):
        return self.cleaned_data.get("suffix_1") or self.cleaned_data.get(
            "recall_period"
        )

    def clean_repeat(self):
        return [r for r in self.cleaned_data.get("repeat", "").split(",") if r]

    def clean_label(self):
        value = self.cleaned_data.get("label")
        if not value:
            self.add_error("label", "English label is required.")
        return value

    def clean_submodule_data(self, name):
        suffix_1 = self.cleaned_data.get("suffix_1")
        suffix_2 = self.cleaned_data.get("suffix_2")
        recall_period = self.cleaned_data.get("recall_period")

        base_name = name
        available_suffix_1 = None

        if name:
            if suffix_1:
                if suffix_1 not in name:
                    self.add_error("suffix_1", "Suffix 1 is not included the in Name")
                else:
                    base_name = base_name.replace(suffix_1, "")

                if not suffix_1.startswith("_"):
                    self.add_error(
                        "suffix_1", "Suffix 1 has to start with an underscore."
                    )

                try:
                    available_suffix_1 = Suffix.objects.get(name__iexact=suffix_1)
                except Suffix.DoesNotExist:
                    available_suffix_1 = suffix_1 in self.available_spreadsheet_suffixes
                    if not available_suffix_1:
                        self.add_error("suffix_1", "Suffix does not exist in the CMS.")

            if suffix_2:
                if not available_suffix_1:
                    self.add_error("suffix_2", "Suffix 1 is required.")

                if suffix_2 not in name:
                    self.add_error("suffix_2", "Suffix 2 is not included in the Name")
                else:
                    base_name = base_name.replace(suffix_2, "")

                if not suffix_2.startswith("_"):
                    self.add_error(
                        "suffix_2", "Suffix 2 has to start with an underscore."
                    )

            if recall_period:
                if recall_period not in name:
                    self.add_error(
                        "recall_period", "Recall period is not included in the Name"
                    )
                else:
                    base_name = base_name.replace(recall_period, "")

                if not recall_period.startswith("_"):
                    self.add_error(
                        "recall_period",
                        "Recall period has to start with an underscore.",
                    )

        self.cleaned_data["base_name"] = base_name
        self.cleaned_data["is_for_sub_question"] = self.is_for_sub_question

    def clean(self):
        cd = super().clean()
        name = cd.get("name")
        type_ = cd.get("type")
        choice_list = cd.get("choice_list")
        relevant = cd.get("relevant")
        constraint = cd.get("constraint")
        submodule_name = cd.get("submodule_name")
        module_name = cd.get("module_name")
        calculation = cd.get("calculation")
        repeat_count = cd.get("repeat_count")

        if type_ in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE):
            if not choice_list:
                self.add_error("choice_list", "This field is required.")
        elif choice_list:
            self.add_error(
                "choice_list", "You cannot add choice_list to that question type."
            )

        if type_ == QuestionType.CALCULATE and not calculation:
            self.add_error("calculation", "This field is required.")

        if type_ == "repeat" and not repeat_count:
            self.add_error("repeat_count", "This field is required.")

        if calculation:
            self.cleaned_data["calculation_dependencies"] = (
                BaseQuestion.get_question_names(calculation)
            )

        if relevant:
            self.cleaned_data["relevant_dependencies"] = (
                BaseQuestion.get_question_names(relevant)
            )

        if constraint:
            self.cleaned_data["constraint_dependencies"] = (
                BaseQuestion.get_question_names(constraint)
            )

        if repeat_count:
            self.cleaned_data["repeat_count_dependencies"] = (
                BaseQuestion.get_question_names(repeat_count)
            )

        if submodule_name:
            submodule = Submodule.objects.filter(name__iexact=submodule_name).first()
            if (
                submodule
                and module_name
                and submodule.module.name.casefold() != module_name.casefold()
            ):
                self.add_error(
                    "submodule_name",
                    f"Submodule ({submodule_name}) already exists and does not belong to the {module_name} module.",
                )
            else:
                self.cleaned_data["submodule"] = submodule
        self.clean_submodule_data(name)
        return self.cleaned_data
