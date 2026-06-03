from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Collate
from django.forms import formset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, reverse
from django.views.generic import FormView
from modules.models import Indicator
from questions.models import (
    BaseQuestion,
    RepeatSection,
    RootQuestionConstraintMessageTranslation,
    SubQuestionConstraintMessageTranslation,
)

from .const import ReferenceQuestionType
from .forms import (
    DownloadTemplateForm,
    QuestionConstraintForm,
    QuestionConstraintTranslationForm,
    QuestionRelevantForm,
    QuestionValidationForm,
    UploadQuestionsForm,
)
from .services import DataImport, QuestionsExport


def _collation_safe_icontains(queryset, search_term, field_names):
    aliases = {
        f"_search_{index}": Collate(field_name, "C")
        for index, field_name in enumerate(field_names)
    }
    queryset = queryset.alias(**aliases)
    predicate = Q.create(
        [(f"{alias}__icontains", search_term) for alias in aliases],
        connector=Q.OR,
    )
    return queryset.filter(predicate)


class AdminQuestionBulkEditMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "/admin/login/"

    def test_func(self):
        return self.request.user.is_staff

    def add_object_permission_errors(self, form, base_questions):
        unauthorized_questions = [
            question.name
            for question in base_questions
            if not self.request.user.has_perm("questions.change_basequestion", question)
        ]
        if not unauthorized_questions:
            return False

        form.add_error(
            None,
            "You do not have permission to change: "
            + ", ".join(unauthorized_questions),
        )
        return True


class ConstraintCreateView(AdminQuestionBulkEditMixin, FormView):
    template_name = "questions/question_constraint.html"
    form_class = QuestionValidationForm

    def get_success_url(self):
        return reverse("admin:questions_basequestion_changelist")

    def get_initial(self):
        initial = super().get_initial()

        ids = self.request.GET.get("ids")
        if ids:
            ids = ids.split(",")
            initial["base_questions"] = BaseQuestion.objects.filter(id__in=ids)
        return initial

    def get_formset_class(self):
        return formset_factory(
            QuestionConstraintForm, extra=0, min_num=1, validate_min=True
        )

    def get_translation_formset_class(self):
        return formset_factory(QuestionConstraintTranslationForm, extra=1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "formset" not in kwargs:
            context["formset"] = self.get_formset_class()()

        if "translation_formset" not in kwargs:
            context["translation_formset"] = self.get_translation_formset_class()(
                prefix="translation"
            )
        return context

    def get_formula(self, form, formset):
        dependencies = []
        formulas = []
        for count, formset_form in enumerate(formset.forms):
            logical_operator = (
                f"{formset_form.cleaned_data['logical_operator']}" if count > 0 else ""
            )

            operator = formset_form.cleaned_data["operator"]
            reference_question = formset_form.cleaned_data["reference_question"]

            right_side_value = ""
            if reference_question == ReferenceQuestionType.OTHER:
                question = formset_form.cleaned_data["question"]
                dependencies.append(question)
                question_name = question.instance.name
                right_side_value = f"${{{question_name}}}"
            elif reference_question == ReferenceQuestionType.SELF:
                right_side_value = f"'{formset_form.cleaned_data['value']}'"

            formulas.append(f"{logical_operator}. {operator} {right_side_value}")

        return " ".join(formulas), dependencies

    def break_down_text_formula(self, form, formula):
        question_names = BaseQuestion.get_question_names(formula)
        base_questions = BaseQuestion.get_base_questions(question_names)
        has_error = False

        for question in base_questions:
            question_names.remove(question.name)

        if question_names:
            message = f"Questions not found: {', '.join(question_names)}"
            form.add_error("constraint", message)
            has_error = True

        if has_error:
            return None, None
        return formula, base_questions

    def create_translations(self, base_question, formset):
        for form in formset.forms:
            if not form.cleaned_data:
                continue

            if base_question.root_question:
                RootQuestionConstraintMessageTranslation.objects.create(
                    root_question=base_question.instance,
                    language=form.cleaned_data["language"],
                    label=form.cleaned_data["label"],
                )
            elif base_question.sub_question:
                SubQuestionConstraintMessageTranslation(
                    sub_question=base_question.instance,
                    language=form.cleaned_data["language"],
                    label=form.cleaned_data["label"],
                )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        formset = self.get_formset_class()(
            request.POST, form_kwargs={"parent_form": form}
        )
        translation_formset = self.get_translation_formset_class()(
            request.POST, prefix="translation"
        )

        if form.is_valid() and translation_formset.is_valid():
            formula = None
            dependencies = None
            base_questions = form.cleaned_data["base_questions"]
            if self.add_object_permission_errors(form, base_questions):
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        formset=formset,
                        translation_formset=translation_formset,
                    )
                )

            if form.cleaned_data["mode"] == "text":
                formula = form.cleaned_data["constraint"]
                formula, dependencies = self.break_down_text_formula(form, formula)
            else:
                if formset.is_valid():
                    formula, dependencies = self.get_formula(form, formset)

            if formula:
                for question in base_questions:
                    question.instance.constraint = formula
                    question.instance.constraint_message = form.cleaned_data[
                        "constraint_message"
                    ]
                    question.instance.updated_by = request.user
                    question.instance.save()
                    self.create_translations(question, translation_formset)

                    if dependencies:
                        question.set_instance_constraint_dependencies(dependencies)
                messages.success(request, "Constraint successfully added.")
                return self.form_valid(form)

        return self.render_to_response(
            self.get_context_data(
                form=form, formset=formset, translation_formset=translation_formset
            )
        )


class RelevantCreateView(AdminQuestionBulkEditMixin, FormView):
    template_name = "questions/question_relevant.html"
    form_class = QuestionRelevantForm

    def get_success_url(self):
        return reverse("admin:questions_basequestion_changelist")

    def get_initial(self):
        initial = super().get_initial()

        ids = self.request.GET.get("ids")
        if ids:
            ids = ids.split(",")
            initial["base_questions"] = BaseQuestion.objects.filter(id__in=ids)
        return initial

    def break_down_text_formula(self, form, formula):
        question_names = BaseQuestion.get_question_names(formula)
        base_questions = BaseQuestion.get_base_questions(question_names)
        has_error = False

        for question in base_questions:
            question_names.remove(question.name)

        if question_names:
            message = f"Questions not found: {', '.join(question_names)}"
            form.add_error("relevant", message)
            has_error = True

        if has_error:
            return None, None
        return formula, base_questions

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            base_questions = form.cleaned_data["base_questions"]
            if self.add_object_permission_errors(form, base_questions):
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                    )
                )

            formula = form.cleaned_data["relevant"]
            formula, dependencies = self.break_down_text_formula(form, formula)

            if formula:
                for question in base_questions:
                    question.instance.relevant = formula
                    question.instance.updated_by = request.user
                    question.instance.save()

                    if dependencies:
                        question.set_instance_relevant_dependencies(dependencies)
                messages.success(request, "Relevant formula successfully added.")
                return self.form_valid(form)

        return self.render_to_response(
            self.get_context_data(
                form=form,
            )
        )


class UploadQuestionsView(UserPassesTestMixin, LoginRequiredMixin, FormView):
    template_name = "questions/upload_questions.html"
    form_class = UploadQuestionsForm
    download_form_class = DownloadTemplateForm

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.can_bulk_upload

    def get_success_url(self):
        return reverse("admin:questions_basequestion_changelist")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_download_form(self, form_class=None):
        if form_class is None:
            form_class = self.download_form_class
        return form_class

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        download_form = self.get_download_form()
        context = {
            "form": form,
            "download_form": download_form,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            form = self.get_form()
            download_form = self.download_form_class(request.POST)
            context_data = {
                "form": form,
                "download_form": download_form,
            }

            if form.is_valid():
                file = form.cleaned_data["file"]
                data_import = DataImport(
                    file, request.user, form.cleaned_data["organizations"]
                )
                data_import.process()

                if data_import.is_valid():
                    (
                        created,
                        created_choices,
                        created_suffixes,
                        created_recall_periods,
                        created_groups,
                        created_indicators,
                    ) = data_import.create()
                    messages.success(request, f"Questions created: {created}")

                    if data_import.existing_questions:
                        messages.success(
                            request,
                            f"Questions already in database: {', '.join(data_import.existing_questions)}",
                        )

                    return self.form_valid(form)
                else:
                    context_data["other_errors"] = data_import.get_errors()

            if download_form.is_valid():
                languages = [
                    lang
                    for lang in settings.LANGUAGES
                    if lang[0] in download_form.cleaned_data["languages"]
                ]
                q_export = QuestionsExport(languages)
                xlsx = q_export.generate_template()

                response = HttpResponse(
                    xlsx,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = (
                    "attachment; filename=codebook_upload_template.xlsx"
                )
                return response

            return self.render_to_response(self.get_context_data(**context_data))


class IndicatorAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Indicator.objects.all()

        if self.q:
            qs = _collation_safe_icontains(qs, self.q, ("name",))

        return qs


# language autocomplete for list of languages
class LanguageAutocomplete(autocomplete.Select2ListView):
    def get(self, request, *args, **kwargs):
        self.q = request.GET.get("q", "")
        query = self.q.lower()
        results = [
            {"id": code, "text": str(label)}
            for code, label in settings.LANGUAGES
            if code != "en"
            and (not query or query in code.lower() or query in str(label).lower())
        ]
        return JsonResponse({"results": results})


class RepeatSectionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = RepeatSection.objects.all()

        if self.q:
            qs = _collation_safe_icontains(qs, self.q, ("name",))

        return qs


class BaseQuestionAutocomplete(autocomplete.Select2QuerySetView):
    paginate_by = 50

    def get_queryset(self):
        qs = BaseQuestion.objects.all()
        search_term = self.request.GET.get("term") or self.q
        if search_term:
            qs = _collation_safe_icontains(
                qs, search_term, ("root_question__name", "sub_question__name")
            )
        return qs
