import enum
from collections import defaultdict

from django.contrib.postgres.aggregates import ArrayAgg
from modules.models import Module, Submodule
from questions.forms import ImportRowForm
from questions.models import (
    BaseQuestion,
    ChoiceGroup,
    RecallPeriod,
    RepeatSection,
    RootQuestion,
    RootQuestionTranslation,
    SubQuestion,
    SubQuestionTranslation,
    Suffix,
)
from questions.services.questions_import.base import (
    ENGLISH_LANGUAGE_CODE,
    BaseImport,
    QuestionImportException,
)


class QuestionsImport(BaseImport):
    columns_mapping = {
        # "<value in spreadsheet>": "<enum attribute>"
        "module_name": "MODULE_NAME",
        "module_label": "MODULE_LABEL",
        "submodule_name": "SUBMODULE_NAME",
        "submodule_label": "SUBMODULE_LABEL",
        "name": "NAME",
        "choice_list": "CHOICE_LIST",
        "type": "TYPE",
        "relevant": "RELEVANT",
        "constraint": "CONSTRAINT",
        "constraint_message": "CONSTRAINT_MESSAGE",
        "calculation": "CALCULATION",
        "description": "DESCRIPTION",
        "suffix1": "SUFFIX_1",
        "suffix2": "SUFFIX_2",
        "recall_period": "RECALL_PERIOD",
        "repeat": "REPEAT",
        "repeat_count": "REPEAT_COUNT",
        "appearance": "APPEARANCE",
        "parameters": "PARAMETERS",
        "default": "DEFAULT",
        "read_only": "READ_ONLY",
        "required": "REQUIRED",
        "disabled": "DISABLED",
    }

    def __init__(
        self,
        question_sheet,
        languages_dict,
        user,
        organizations,
        *args,
        **kwargs,
    ):
        super().__init__(user, *args, **kwargs)
        self.work_sheet = question_sheet
        self.languages_dict = languages_dict

        self.existing_questions = []
        self.cleaned_data = []
        self.errors = {}
        self.non_form_errors = []

        self.columns = None
        self.language_columns = None
        self.hint_columns = None

        self.processed_question_names = set()
        self.names_required_for_sub_questions = set()
        self.root_question_names = set()
        self.required_relevant_question_names = set()
        self.required_constraint_question_names = set()
        self.required_calculation_question_names = set()
        self.choice_lists_to_validate = set()
        self.module_names_to_validate = set()
        self.submodule_names_to_validate = set()
        self.created_submodules = {}

        self.root_questions_after_sub_question = set()

        self.required_repeat_count_question_names = set()
        self.processed_repeat_names = set()
        self.required_repeat = set()

        self.repeat_to_create = []
        self.repeat_questions_to_set = defaultdict(list)
        self.questions_to_exclude_from_repeats = []

        self.submodule_order = (
            max(Submodule.objects.values_list("order", flat=True) or [0]) + 1
        )
        self.organizations = organizations

    def get_row_form(self, row):
        data = {
            "module_name": self.get_value(row, self.columns.MODULE_NAME),
            "module_label": self.get_value(row, self.columns.MODULE_LABEL),
            "submodule_name": self.get_value(row, self.columns.SUBMODULE_NAME),
            "submodule_label": self.get_value(row, self.columns.SUBMODULE_LABEL),
            "name": self.get_value(row, self.columns.NAME),
            "label": self.get_value(row, self.language_columns[ENGLISH_LANGUAGE_CODE]),
            "hint": self.get_value(row, self.hint_columns[ENGLISH_LANGUAGE_CODE]),
            "choice_list": self.get_value(row, self.columns.CHOICE_LIST),
            "type": self.get_value(row, self.columns.TYPE),
            "relevant": self.get_value(row, self.columns.RELEVANT),
            "constraint": self.get_value(row, self.columns.CONSTRAINT),
            "constraint_message": self.get_value(row, self.columns.CONSTRAINT_MESSAGE),
            "calculation": self.get_value(row, self.columns.CALCULATION),
            "description": self.get_value(row, self.columns.DESCRIPTION),
            "suffix_1": self.get_value(row, self.columns.SUFFIX_1),
            "suffix_2": self.get_value(row, self.columns.SUFFIX_2),
            "recall_period": self.get_value(row, self.columns.RECALL_PERIOD),
            "repeat": self.get_value(row, self.columns.REPEAT),
            "repeat_count": self.get_value(row, self.columns.REPEAT_COUNT),
            "appearance": self.get_value(row, self.columns.APPEARANCE),
            "parameters": self.get_value(row, self.columns.PARAMETERS),
            "default": self.get_value(row, self.columns.DEFAULT),
            "read_only": self.get_value(row, self.columns.READ_ONLY),
            "required": self.get_value(row, self.columns.REQUIRED),
            "disabled": self.get_value(row, self.columns.DISABLED),
        }

        return ImportRowForm(data=data)

    def populate_data_for_validation(self, cleaned_data, is_for_sub_question):
        name = cleaned_data.get("name")
        module_name = cleaned_data.get("module_name")
        submodule_name = cleaned_data.get("submodule_name")
        type_ = cleaned_data.get("type_")
        relevant_dependencies = cleaned_data.get("relevant_dependencies", [])
        constraint_dependencies = cleaned_data.get("constraint_dependencies", [])
        calculation_dependencies = cleaned_data.get("calculation_dependencies", [])
        choice_list = cleaned_data.get("choice_list")
        base_name = cleaned_data.get("base_name")  # only for sub questions

        if name:
            self.processed_question_names.add(name)
            if is_for_sub_question:
                self.names_required_for_sub_questions.add(base_name)
                if base_name not in self.root_question_names:
                    self.root_questions_after_sub_question.add(base_name)
            else:
                self.root_question_names.add(name)

        if choice_list:
            self.choice_lists_to_validate.add(choice_list)
        self.module_names_to_validate.add(module_name)
        self.submodule_names_to_validate.add(submodule_name)
        self.required_relevant_question_names.update(relevant_dependencies)
        self.required_constraint_question_names.update(constraint_dependencies)
        self.required_calculation_question_names.update(calculation_dependencies)

        repeat_count_dependencies = cleaned_data.get("repeat_count_dependencies", [])
        self.required_repeat_count_question_names.update(repeat_count_dependencies)

        repeat = cleaned_data.get("repeat")

        if type_ == "repeat":
            self.processed_repeat_names.add(name)

        if repeat:
            self.required_repeat.update(repeat)

    def _validate_repeat(self):
        missing_repeat = self.processed_repeat_names.difference(self.required_repeat)
        if missing_repeat:
            self.non_form_errors.append(
                f"Repeat Section | Missing: {', '.join(missing_repeat)}"
            )

    def _validate_root_questions(self):
        """
        Validate (for change request) that all root_question modules
        (if root_question exists) matches declared organizations set.
        """
        existing_questions_to_validate = RootQuestion.objects.filter(
            name__in=self.root_question_names
        )
        annotated_questions_to_validate = existing_questions_to_validate.annotate(
            organization_ids=ArrayAgg(
                "submodule__module__organizations__id", distinct=True
            )
        )
        mismatched_organization_questions = annotated_questions_to_validate.exclude(
            organization_ids=list(self.organizations.values_list("id", flat=True)),
        )

        for mismatched_orgs_question in mismatched_organization_questions:
            self.non_form_errors.append(
                f"Cannot process existing question ({mismatched_orgs_question.name}), "
                "because this question's modules belongs to different organizations than declared."
                "If you want to add this question to submodule belonging to different organizations subset, "
                "please ask global admin to do it through CMS interface.",
            )

    def _validate_organization_permissions(self):
        """
        Validation function for permissions related to shared organizations' logic.
        """

        restricted_modules = Module.objects.exclude_by_organization_ids(
            list(self.organizations.values_list("id", flat=True))
        )

        # Validate usage of restricted modules in questions + validate creating submodules in restricted modules
        for module in restricted_modules.filter(name__in=self.module_names_to_validate):
            self.non_form_errors.append(
                f"User has no permission to upload content to module ({module.name}), "
                f"because module belongs to other organization, or more than one organization.",
            )

    def _validate_submodules(self):
        # Validate submodule-module pair, submodule should not be combined with module other than in DB
        for submodule in Submodule.objects.exclude(
            module__name__in=self.module_names_to_validate
        ).filter(name__in=self.submodule_names_to_validate):
            self.non_form_errors.append(
                f"Mismatch between submodule-module pair "
                f"already existing in database for submodule {submodule.name}"
            )

    def _validate_choices(self, available_spreadsheet_choices: set):
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

    def _check_missing_repeat_count_dependencies(self):
        missing_relevant_names = self.required_relevant_question_names.difference(
            self.processed_question_names
        )
        db_questions_relevant_names = {
            q.name for q in BaseQuestion.objects.filter_by_names(missing_relevant_names)
        }
        missing_relevant_names = missing_relevant_names.difference(
            db_questions_relevant_names
        )

        if missing_relevant_names:
            self.non_form_errors.append(
                f"Missing questions used in relevant column: {', '.join(missing_relevant_names)}"
            )

    def _check_missing_dependencies(self):
        missing_relevant_names = self.required_relevant_question_names.difference(
            self.processed_question_names
        )
        db_questions_relevant_names = {
            q.name for q in BaseQuestion.objects.filter_by_names(missing_relevant_names)
        }
        missing_relevant_names = missing_relevant_names.difference(
            db_questions_relevant_names
        )

        missing_constraint_names = self.required_constraint_question_names.difference(
            self.processed_question_names
        )
        db_questions_constraint_names = {
            q.name
            for q in BaseQuestion.objects.filter_by_names(missing_constraint_names)
        }
        missing_constraint_names = missing_constraint_names.difference(
            db_questions_constraint_names
        )

        missing_calculation_names = self.required_calculation_question_names.difference(
            self.processed_question_names
        )
        db_questions_calculation_names = {
            q.name
            for q in BaseQuestion.objects.filter_by_names(missing_calculation_names)
        }
        missing_calculation_names = missing_calculation_names.difference(
            db_questions_calculation_names
        )

        if missing_relevant_names:
            self.non_form_errors.append(
                f"Missing questions used in relevant column: {', '.join(missing_relevant_names)}"
            )

        if missing_constraint_names:
            self.non_form_errors.append(
                f"Missing questions used in constraint column: {', '.join(missing_constraint_names)}"
            )

        if missing_calculation_names:
            self.non_form_errors.append(
                f"Missing questions used in calculation column: {', '.join(missing_calculation_names)}"
            )

    def _check_sub_questions_dependencies(self):
        names_diff = self.names_required_for_sub_questions.difference(
            self.root_question_names
        )
        root_questions_after_sub_question = self.root_questions_after_sub_question

        if names_diff:
            root_question_names = set(
                RootQuestion.objects.filter(name__in=names_diff).values_list(
                    "name", flat=True
                )
            )
            names_diff = names_diff.difference(root_question_names)

            root_questions_after_sub_question = (
                root_questions_after_sub_question.difference(root_question_names)
            )

            if names_diff:
                self.non_form_errors.append(
                    f"Missing questions (required to create sub questions): {', '.join(names_diff)}"
                )

        if root_questions_after_sub_question:
            self.non_form_errors.append(
                f"Root Questions placed after Sub Questions: {','.join(root_questions_after_sub_question)} | Please change ordering."
            )

    def process(self, available_spreadsheet_choices, available_spreadsheet_suffixes):
        try:
            self.validate_and_set_columns()
        except QuestionImportException as error:
            self.non_form_errors.append(str(error))
            return

        for counter, row in enumerate(self.work_sheet.iter_rows(min_row=2), 2):
            if not self.get_value(row, self.columns.NAME):
                continue
            form = self.get_row_form(row)
            form.set_available_spreadsheet_suffixes(available_spreadsheet_suffixes)

            if form.is_valid():
                cleaned_data = form.cleaned_data
                translations = []
                hints = {}

                for lang_col in self.language_columns:
                    if lang_col.name == ENGLISH_LANGUAGE_CODE:
                        continue

                    translation = self.get_value(row, lang_col)
                    if translation:
                        translations.append((lang_col.name, translation))

                for lang_col in self.hint_columns:
                    hint = self.get_value(row, lang_col)

                    if lang_col.name == ENGLISH_LANGUAGE_CODE:
                        cleaned_data["hint"] = hint

                    if hint:
                        hints[lang_col.name] = hint

                cleaned_data["translations"] = translations
                cleaned_data["hints"] = hints
                self.cleaned_data.append(cleaned_data)
            else:
                self.errors[counter] = form.errors

            self.populate_data_for_validation(
                form.cleaned_data, is_for_sub_question=form.is_for_sub_question
            )

        self._check_missing_dependencies()
        self._check_sub_questions_dependencies()
        self._check_missing_repeat_count_dependencies()
        self._validate_repeat()
        self._validate_submodules()
        self._validate_organization_permissions()
        self._validate_root_questions()

        if self.choice_lists_to_validate:
            self._validate_choices(available_spreadsheet_choices)

    def create_sub_question(
        self,
        root_question_name,
        name,
        suffix_1_instance,
        suffix_2_instance,
        recall_period,
        description,
        label,
        hint,
        relevant,
        constraint,
        constraint_message,
        calculation,
        translations,
        hints: dict,
        appearance,
        parameters,
        default,
        disabled,
        required,
        read_only,
        skip_saving=False,
    ):
        root_question = (
            RootQuestion.objects.get(name__iexact=root_question_name)
            if not skip_saving
            else None
        )
        recall_period_instance = None

        if recall_period:
            try:
                recall_period_instance = RecallPeriod.objects.get(
                    name__iexact=recall_period
                )
            except RecallPeriod.DoesNotExist:
                if skip_saving:
                    self.log_change(RecallPeriod, recall_period, create=True)
                else:
                    recall_period_instance = RecallPeriod.objects.create(
                        name=recall_period, **self.user_tracking_kwargs
                    )
                    self.log_addition(recall_period_instance)

        if skip_saving:
            self.log_change(SubQuestion, name, create=True)
            return

        question, created = SubQuestion.objects.update_or_create(
            name=name,
            root_question=root_question,
            suffix=suffix_1_instance,
            suffix_2=suffix_2_instance,
            recall_period=recall_period_instance,
            defaults={
                "description": description,
                "label": label,
                "hint": hint or "",
                "relevant": relevant,
                "constraint": constraint,
                "constraint_message": constraint_message,
                "calculation": calculation,
                "appearance": appearance,
                "parameters": parameters,
                "default": default,
                "disabled": disabled,
                "required": required,
                "read_only": read_only,
                **self.user_tracking_kwargs,
            },
        )

        self.log_addition(question)

        for language_code, translation in translations:
            hint_ = hints.get(language_code, "")
            translation_, _ = SubQuestionTranslation.objects.update_or_create(
                sub_question=question,
                language=language_code,
                defaults={
                    "label": translation,
                    "hint": hint_,
                    **self.user_tracking_kwargs,
                },
            )
            self.log_addition(translation_)

        return question

    def create_root_question(
        self,
        submodule,
        name,
        description,
        label,
        hint,
        type_,
        choice_list,
        relevant,
        constraint,
        constraint_message,
        calculation,
        translations,
        hints: dict,
        appearance,
        parameters,
        default,
        disabled,
        required,
        read_only,
        skip_saving=False,
    ):
        if skip_saving:
            self.log_change(RootQuestion, name, create=True)
            return

        question, created = RootQuestion.objects.update_or_create(
            name=name,
            defaults={
                "description": description,
                "label": label,
                "hint": hint or "",
                "type": type_,
                "choices": choice_list,
                "relevant": relevant,
                "constraint": constraint,
                "constraint_message": constraint_message,
                "calculation": calculation,
                "appearance": appearance,
                "parameters": parameters,
                "default": default,
                "disabled": disabled,
                "required": required,
                "read_only": read_only,
                **self.user_tracking_kwargs,
            },
        )
        question.submodule.add(submodule.id)

        self.log_addition(question)

        for language_code, translation in translations:
            hint_ = hints.get(language_code, "")
            translation_, _ = RootQuestionTranslation.objects.update_or_create(
                root_question=question,
                language=language_code,
                defaults={
                    "label": translation,
                    "hint": hint_,
                    **self.user_tracking_kwargs,
                },
            )

            self.log_addition(translation_)

        return question

    def create_repeat_sections(self, skip_saving=False):
        for rs_data in self.repeat_to_create:
            name = rs_data["name"]

            if skip_saving:
                self.log_change(RepeatSection, rs_data["name"], create=True)
            else:
                repeat_section, created = self.permissions_based_method(
                    name=name,
                    defaults={
                        "repeat_count": rs_data["repeat_count"],
                        "description": rs_data["description"],
                        "relevant": rs_data["relevant"],
                        "label": rs_data["label"],
                        **self.user_tracking_kwargs,
                    },
                )
                repeat_section.submodule.add(rs_data["submodule"])

                self.log_addition(repeat_section)
                repeat_section.set_repeat_count_dependencies()
                questions_ids_to_set = {
                    q.id for q in self.repeat_questions_to_set[rs_data["name"]]
                }
                if created:
                    repeat_section.questions.set(questions_ids_to_set)
                else:
                    base_questions = repeat_section.questions.exclude(
                        id__in=self.questions_to_exclude_from_repeats
                    ) | BaseQuestion.objects.filter(id__in=questions_ids_to_set)

                    repeat_section.questions.set(base_questions)

    def get_processed_names(self) -> list[str]:
        return [d["name"] for d in self.cleaned_data if d["name"]] + [
            item for d in self.cleaned_data if "repeat" in d for item in d["repeat"]
        ]

    def create(self, created_choices: dict, created_suffixes: dict, skip_saving=False):
        imported = 0
        data_for_further_processing = []

        for data in self.cleaned_data:
            name = data["name"]

            if BaseQuestion.objects.filter_by_names([name]).exists():
                self.existing_questions.append(name)

                if skip_saving:
                    self.log_change(BaseQuestion, name, create=False)
                    continue

            submodule = data["submodule"] or self.create_submodule(data, skip_saving)
            description = data.get("description", "")
            label = data["label"]
            hint = data.get("hint", "")
            type_ = data["type"]
            choice_list = self.get_choices(
                data.get("choice_list"), created_choices, skip_saving
            )
            relevant = data.get("relevant", "")
            relevant_dependencies = data.get("relevant_dependencies")
            constraint = data.get("constraint", "")
            constraint_message = data.get("constraint_message", "")
            constraint_dependencies = data.get("constraint_dependencies")
            calculation = data.get("calculation")
            calculation_dependencies = data.get("calculation_dependencies")
            is_for_sub_question = data.get("is_for_sub_question")
            suffix_1_instance = self.get_suffix(
                data.get("suffix_1"), created_suffixes, skip_saving
            )
            suffix_2_instance = self.get_suffix(
                data.get("suffix_2"), created_suffixes, skip_saving
            )
            recall_period = data.get("recall_period")
            base_name = data.get("base_name")
            repeat = data.get("repeat")
            repeat_count = data.get("repeat_count")
            appearance = data.get("appearance")
            parameters = data.get("parameters")
            default = data.get("default", "")
            disabled = data.get("disabled", "")
            required = data.get("required", "")
            read_only = data.get("read_only", "")

            question = None
            root_question_args = {
                "submodule": submodule,
                "name": name,
                "description": description,
                "label": label,
                "hint": hint,
                "type_": type_,
                "choice_list": choice_list,
                "relevant": relevant,
                "constraint": constraint,
                "constraint_message": constraint_message,
                "calculation": calculation,
                "translations": data["translations"],
                "hints": data["hints"],
                "appearance": appearance,
                "parameters": parameters,
                "default": default,
                "disabled": disabled,
                "required": required,
                "read_only": read_only,
                "skip_saving": skip_saving,
            }
            if type_ == "repeat":
                self.repeat_to_create.append(
                    {
                        "submodule": submodule,
                        "repeat_count": repeat_count,
                        "name": name,
                        "description": description,
                        "relevant": relevant,
                        "label": label,
                    }
                )
            elif is_for_sub_question:
                question = self.create_sub_question(
                    root_question_name=base_name,
                    name=name,
                    suffix_1_instance=suffix_1_instance,
                    suffix_2_instance=suffix_2_instance,
                    recall_period=recall_period,
                    description=description,
                    label=label,
                    hint=hint,
                    relevant=relevant,
                    constraint=constraint,
                    constraint_message=constraint_message,
                    calculation=calculation,
                    translations=data["translations"],
                    hints=data["hints"],
                    appearance=appearance,
                    parameters=parameters,
                    default=default,
                    disabled=disabled,
                    required=required,
                    read_only=read_only,
                    skip_saving=skip_saving,
                )
            else:
                question = self.create_root_question(**root_question_args)
            if question:
                if (
                    relevant_dependencies
                    or constraint_dependencies
                    or calculation_dependencies
                ):
                    data_for_further_processing.append(
                        (
                            question,
                            relevant_dependencies,
                            constraint_dependencies,
                            calculation_dependencies,
                        )
                    )

                if repeat:
                    for r in repeat:
                        self.repeat_questions_to_set[r].append(question.base_question)
                else:
                    lookup = (
                        "root_question__id"
                        if isinstance(question, RootQuestion)
                        else "sub_question__id"
                    )
                    base_question = BaseQuestion.objects.filter(
                        **{lookup: question.id}
                    ).first()
                    self.questions_to_exclude_from_repeats.append(base_question.id)

                imported += 1

        for data in data_for_further_processing:
            (
                question,
                relevant_dependencies,
                constraint_dependencies,
                calculation_dependencies,
            ) = data

            if relevant_dependencies:
                question.relevant_dependencies.set(
                    q.id
                    for q in BaseQuestion.objects.filter_by_names(relevant_dependencies)
                )

            if constraint_dependencies:
                question.constraint_dependencies.set(
                    q.id
                    for q in BaseQuestion.objects.filter_by_names(
                        constraint_dependencies
                    )
                )
            if calculation_dependencies:
                question.calculation_dependencies.set(
                    q.id
                    for q in BaseQuestion.objects.filter_by_names(
                        calculation_dependencies
                    )
                )

        self.create_repeat_sections(skip_saving=skip_saving)

        return imported

    def _get_language_code(self, value, prefix, inv_languages_dict):
        parts = value.replace(prefix, "").replace(")", "").split("(")
        parts.append("")
        language_display, language_code, *rest = parts
        language_display = language_display.strip()
        language_code = language_code.strip()

        code = self.languages_dict.get(language_code) or inv_languages_dict.get(
            language_display
        )

        if not code:
            raise QuestionImportException(f"Language not found for column: {value}")

        return language_code or code

    def validate_and_set_columns(self):
        columns = []
        language_columns = []
        hint_columns = []

        language_label_prefix = "label::"
        hint_prefix = "hint::"
        inv_languages_dict = {v: k for k, v in self.languages_dict.items()}
        for counter, cell in enumerate(self.work_sheet[1]):
            if not cell.value:
                continue
            key = self.columns_mapping.get(cell.value.lower())
            if key:
                columns.append((key, counter))
                continue

            if language_label_prefix in cell.value:
                code = self._get_language_code(
                    cell.value, language_label_prefix, inv_languages_dict
                )
                language_columns.append((code, counter))
            elif hint_prefix in cell.value:
                code = self._get_language_code(
                    cell.value, hint_prefix, inv_languages_dict
                )
                hint_columns.append((code, counter))

        if len(self.columns_mapping) != len(columns):
            raise QuestionImportException(
                "Incorrect survey spreadsheet. Missing columns."
            )

        if not language_columns:
            raise QuestionImportException(
                "Question translation column missing or incorrect."
            )

        if not hint_columns:
            raise QuestionImportException("Question hint column missing or incorrect.")

        self.columns = enum.Enum("COLUMNS", columns)
        self.language_columns = enum.Enum("LANGUAGE_COLUMNS", language_columns)
        self.hint_columns = enum.Enum("HINT_COLUMNS", hint_columns)

    def create_submodule(self, data, skip_saving=False):
        module_label = data["module_label"]
        module_name = data["module_name"]
        submodule_name = data["submodule_name"]
        submodule_label = data["submodule_label"]

        created_submodule = self.created_submodules.get(submodule_name)
        if created_submodule:
            return created_submodule

        module = None
        try:
            module = Module.objects.get(name__iexact=module_name)
        except Module.DoesNotExist:
            if skip_saving:
                self.log_change(Module, module_name, create=True)
            else:
                module = Module.objects.create(
                    name=module_name, label=module_label, **self.user_tracking_kwargs
                )
                module.organizations.set(self.organizations)
                self.log_addition(module)

        submodule = None
        try:
            submodule = Submodule.objects.get(name__iexact=submodule_name)
        except Submodule.DoesNotExist:
            if skip_saving:
                self.log_change(Submodule, submodule_name, create=True)
            else:
                submodule = Submodule.objects.create(
                    name=submodule_name,
                    module=module,
                    label=submodule_label,
                    order=self.submodule_order,
                    **self.user_tracking_kwargs,
                )
                self.log_addition(submodule)
                self.submodule_order += 1

                self.log_addition(submodule)
                self.created_submodules[submodule_name] = submodule

        return submodule

    def get_suffix(self, name, created_suffixes, skip_saving=False):
        if name and not skip_saving:
            return created_suffixes.get(name) or Suffix.objects.get(name__iexact=name)
        return

    def get_choices(self, name, created_choices, skip_saving=False):
        if name and not skip_saving:
            return created_choices.get(name) or ChoiceGroup.objects.get(
                name__iexact=name
            )
        return

    @property
    def permissions_based_method(self):
        if self.user.is_global_admins_member or self.user.is_superuser:
            return RepeatSection.objects.update_or_create
        return RepeatSection.objects.get_or_create
