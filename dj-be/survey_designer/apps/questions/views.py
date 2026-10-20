import json
from collections import defaultdict

from dal import autocomplete
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Collate
from django.forms import formset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, reverse
from django.urls import NoReverseMatch
from django.views.decorators.http import require_GET, require_POST
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
from .services.expression_scope import (
    expression_references,
    load_reference_scope,
    sync_expression_dependencies,
    validate_expression_fields,
)
from .services.health import (
    MODEL_ORDER,
    MODEL_SPECS,
    HealthScanInfrastructureError,
    count_totals,
    scan_batch,
)


def _health_user_can_access(user):
    """Require global admin authority and view permission for every scan model."""

    if not user or not user.is_authenticated:
        return False
    if not (user.is_superuser or user.is_global_admins_member):
        return False
    return all(
        user.has_perm(
            f"{spec.model._meta.app_label}.view_{spec.model._meta.model_name}"
        )
        for spec in MODEL_SPECS.values()
    )


def _health_headers(response):
    response["Cache-Control"] = "no-store, private"
    response["Pragma"] = "no-cache"
    return response


def _health_error(message, status, **extra):
    body = {"status": "error", "message": message, **extra}
    return _health_headers(JsonResponse(body, status=status))


def _health_edit_url(request, model, obj, field=""):
    """Build a link only when the registered admin allows this object to change."""

    if obj is None:
        return None
    model_admin = admin.site._registry.get(model)
    if model_admin is None:
        return None
    try:
        if not model_admin.has_change_permission(request, obj):
            return None
        url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_change",
            args=[obj.pk],
        )
    except (LookupError, NoReverseMatch, PermissionDenied):
        return None
    if field:
        url = f"{url}#id_{field}"
    return url


def _health_add_edit_links(request, payload, objects):
    """Decorate findings from the page's already-loaded objects.

    This callback runs inside the scanner's read-only transaction, so link
    permission checks share the same timeout and transaction guard as the
    validation queries.
    """

    permissions = {}
    resolved = {}

    def resolve_object(finding):
        key = (finding.get("model"), finding.get("id"))
        if key in objects:
            return objects[key]
        if key in resolved:
            return resolved[key]
        spec = MODEL_SPECS.get(finding.get("model"))
        object_id = finding.get("id")
        if (
            spec is None
            or not isinstance(object_id, int)
            or isinstance(object_id, bool)
            or object_id <= 0
        ):
            resolved[key] = None
            return None
        # Dependency graph errors may refer to an object outside this page.
        # Load only the identity fields needed by the registered admin's
        # permission check; this callback remains inside the scan guard.
        resolved[key] = (
            spec.model.objects.only("id", "name").filter(pk=object_id).first()
        )
        return resolved[key]

    for findings, field_anchor in (
        (payload.get("issues", []), True),
        (payload.get("scan_errors", []), False),
    ):
        for finding in findings:
            obj = resolve_object(finding)
            if obj is None:
                continue
            key = (finding.get("model"), obj.pk)
            if key not in permissions:
                permissions[key] = _health_edit_url(request, type(obj), obj)
            if permissions[key]:
                finding["edit_url"] = (
                    f"{permissions[key]}#id_{finding.get('field')}"
                    if field_anchor
                    else permissions[key]
                )
    return payload


@require_GET
def survey_health(request):
    """Render the idle health page; scans only happen through the POST endpoint."""

    if not _health_user_can_access(request.user):
        raise PermissionDenied
    context = admin.site.each_context(request)
    context.update(
        {
            "title": "Survey health",
            "health_models": [
                {"key": key, "label": MODEL_SPECS[key].label} for key in MODEL_ORDER
            ],
            "health_scan_url": reverse("survey-health-scan"),
        }
    )
    return _health_headers(render(request, "admin/survey_health.html", context))


@require_POST
def survey_health_scan(request):
    """Scan one bounded page for the authorized admin browser session."""

    if not _health_user_can_access(request.user):
        raise PermissionDenied
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _health_error("Invalid health scan request.", 400)
    if not isinstance(data, dict):
        return _health_error("Invalid health scan request.", 400)
    if data.get("action") == "totals":
        try:
            totals = count_totals()
        except HealthScanInfrastructureError as error:
            return _health_error(str(error), 503, complete=False)
        return _health_headers(JsonResponse({"status": "ok", "totals": totals}))
    model_key = data.get("model")
    if not isinstance(model_key, str) or model_key not in MODEL_SPECS:
        return _health_error("Unknown health scan model.", 400)
    try:
        payload = scan_batch(
            model_key,
            after_pk=data.get("after_pk", 0),
            requested_limit=data.get("limit", 25),
            decorate=lambda result, objects: _health_add_edit_links(
                request, result, objects
            ),
        )
    except HealthScanInfrastructureError as error:
        return _health_error(str(error), 503, complete=False)
    payload["status"] = "ok"
    return _health_headers(JsonResponse(payload))


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

    def add_expression_errors(self, form, field_name, formula, base_questions):
        """Validate the formula for every selected question before saving it."""
        error_field = field_name if field_name in form.fields else None
        has_error = False
        scope = load_reference_scope(expression_references({field_name: formula}))
        repeats_by_question = defaultdict(list)
        for (
            base_question_id,
            repeat_name,
        ) in RepeatSection.questions.through.objects.filter(
            basequestion__in=base_questions
        ).values_list(
            "basequestion_id", "repeatsection__name"
        ):
            repeats_by_question[base_question_id].append(repeat_name)
        for base_question in base_questions:
            instance = base_question.instance
            if isinstance(instance, RepeatSection):
                # A repeat's relevance is evaluated outside the repeat.
                question_kwargs = {
                    "members": [member.name for member in instance.questions.all()]
                }
            else:
                question_kwargs = {
                    "question_type": instance.type or "",
                    "repeats": repeats_by_question[base_question.id],
                }
            issues = validate_expression_fields(
                {
                    "model": instance.__class__.__name__,
                    "id": instance.id,
                    "name": instance.name,
                },
                {field_name: formula},
                scope=scope,
                **question_kwargs,
            )
            for issue in issues:
                form.add_error(error_field, issue.message)
                has_error = True
        return has_error


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
        formulas = []
        for count, formset_form in enumerate(formset.forms):
            logical_operator = (
                f"{formset_form.cleaned_data['logical_operator']} " if count > 0 else ""
            )

            operator = formset_form.cleaned_data["operator"]
            reference_question = formset_form.cleaned_data["reference_question"]

            right_side_value = ""
            if reference_question == ReferenceQuestionType.OTHER:
                question = formset_form.cleaned_data["question"]
                question_name = question.instance.name
                right_side_value = f"${{{question_name}}}"
            elif reference_question == ReferenceQuestionType.SELF:
                right_side_value = f"'{formset_form.cleaned_data['value']}'"

            formulas.append(f"{logical_operator}. {operator} {right_side_value}")

        return " ".join(formulas)

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
            elif formset.is_valid():
                formula = self.get_formula(form, formset)

            if formula and not self.add_expression_errors(
                form, "constraint", formula, base_questions
            ):
                for question in base_questions:
                    question.instance.constraint = formula
                    question.instance.constraint_message = form.cleaned_data[
                        "constraint_message"
                    ]
                    question.instance.updated_by = request.user
                    question.instance.save()
                    self.create_translations(question, translation_formset)
                    sync_expression_dependencies(question.instance)
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
            if not self.add_expression_errors(
                form, "relevant", formula, base_questions
            ):
                for question in base_questions:
                    question.instance.relevant = formula
                    question.instance.updated_by = request.user
                    question.instance.save()
                    sync_expression_dependencies(question.instance)
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
