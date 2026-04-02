import pytest
from core.utils import get_model_admin_base_url
from django.test import TestCase
from modules.models import Module, Submodule
from organization.models import Organization
from questions.const import QuestionType
from questions.models import RootQuestion, RootQuestionTranslation, SubQuestion, Suffix


def _admin_post_change_or_fail(
    client,
    obj,
    override: dict | None = None,
    *,
    submodule_ids: list[int] | None = None,
    type_override: str | None = None,
):
    """
    Submit the Django admin change form for `obj` and assert it saved.

    A 302 redirect indicates a successful admin form submission. If the response
    is not 302, this helper raises AssertionError and includes admin form errors
    (when available) to speed up debugging.

    Args:
        client: Django test client authenticated as an admin user.
        obj: The model instance being edited through the admin change form.
        override: Optional dict of fields to override in the POST payload.
        submodule_ids: Optional list of Submodule primary keys for the M2M field.
            If omitted, the object's current submodule relation is used.
        type_override: Optional question type to set explicitly. If the type is a
            `select_*` variant, you must also include a valid `choices` field in
            `override` to satisfy admin validation.

    Returns:
        The HTTP response from the admin POST (status 302).
    """
    url = get_model_admin_base_url(type(obj), "_change", [obj.id])

    # Use existing M2M if not explicitly provided
    if submodule_ids is None:
        submodule_ids = list(obj.submodule.values_list("id", flat=True))

    # Base payload + inline management forms (no inlines in these tests)
    payload = {
        "name": obj.name,
        "description": obj.description or "",
        "label": obj.label or "",
        "type": type_override or obj.type or "integer",
        "submodule": [str(sid) for sid in submodule_ids],
        "base_question-TOTAL_FORMS": 0,
        "base_question-INITIAL_FORMS": 0,
        "constraint_translations-TOTAL_FORMS": 0,
        "constraint_translations-INITIAL_FORMS": 0,
        "translations-TOTAL_FORMS": 0,
        "translations-INITIAL_FORMS": 0,
        "sub_questions-TOTAL_FORMS": 0,
        "sub_questions-INITIAL_FORMS": 0,
    }
    if override:
        payload.update(override)

    resp = client.post(url, payload, follow=False)
    if resp.status_code != 302:
        # Include admin form errors (if present) for faster diagnosis
        try:
            form_errors = resp.context["adminform"].form.errors
        except Exception:
            form_errors = resp.content.decode("utf-8", errors="ignore")[:2000]
        raise AssertionError(
            f"Admin POST did not save (status {resp.status_code}). "
            f"URL={url}\nErrors:\n{form_errors}\nPayload keys: {sorted(payload.keys())}"
        )
    return resp


def _ensure_translation(root_question, language: str, label: str, hint: str):
    """
    Upsert a RootQuestionTranslation for (root_question, language).

    Prevents violating the unique (root_question, language) constraint when a
    translation row for the same language already exists. Only updates the
    fields relevant to the test (label) and uses update_fields to keep
    DB writes minimal.
    """
    obj, created = RootQuestionTranslation.objects.get_or_create(
        root_question=root_question,
        language=language,
        defaults={"label": label, "hint": hint},
    )
    updates = {}
    if hasattr(obj, "label") and obj.label != label:
        updates["label"] = label
    if updates:
        for k, v in updates.items():
            setattr(obj, k, v)
        obj.save(update_fields=list(updates.keys()))
    return obj


# ---- Tests -------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_rename_propagates_to_equations_and_translations(
    logged_admin_client,
    submodule_1,
    root_question_1,  # Q1 (will be renamed)
    root_question_2,  # Q2 (references Q1)
):
    # Configure Q2 via the admin to reference Q1 in all equation fields
    old = root_question_1.name

    override_q2 = {
        "constraint": f"${{{old}}} = 5",
        "relevant": f"${{{old}}} > 10",
        "choice_filter": f"${{{old}}} in some_filter",
        "calculation": f"${{{old}}} + 1",
    }
    type_override = None
    if root_question_2.type in ("select_one", "select_multiple"):
        type_override = root_question_2.type
        override_q2["choices"] = root_question_2.choices_id

    _admin_post_change_or_fail(
        logged_admin_client,
        root_question_2,
        override=override_q2,
        submodule_ids=[submodule_1.id],
        type_override=type_override,
    )

    root_question_2.refresh_from_db()
    assert root_question_2.relevant == f"${{{old}}} > 10"
    assert root_question_2.constraint == f"${{{old}}} = 5"
    assert root_question_2.choice_filter == f"${{{old}}} in some_filter"
    assert root_question_2.calculation == f"${{{old}}} + 1"

    # Admin save_model sets dependency M2Ms from equation parsing
    assert root_question_2.relevant_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()
    assert root_question_2.constraint_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()
    assert root_question_2.choice_filter_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()
    assert root_question_2.calculation_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()

    # Translation for Q2 that references Q1
    t_en = _ensure_translation(
        root_question_2,
        "en",
        label=f"EN label uses ${{{old}}}",
        hint=f"EN hint uses ${{{old}}}",
    )

    # Rename Q1 via admin
    new = f"{old}_NEW"
    q1_submodules = list(root_question_1.submodule.values_list("id", flat=True)) or [
        submodule_1.id
    ]
    _admin_post_change_or_fail(
        logged_admin_client,
        root_question_1,
        override={
            "name": new,
            **(
                {"type": root_question_1.type, "choices": root_question_1.choices_id}
                if root_question_1.type in ("select_one", "select_multiple")
                else {"type": root_question_1.type or "integer"}
            ),
        },
        submodule_ids=q1_submodules,
    )

    # Q2 equations and translation label reflect the renamed token
    root_question_2.refresh_from_db()
    t_en.refresh_from_db()

    assert root_question_2.relevant == f"${{{new}}} > 10"
    assert root_question_2.constraint == f"${{{new}}} = 5"
    assert root_question_2.choice_filter == f"${{{new}}} in some_filter"
    assert root_question_2.calculation == f"${{{new}}} + 1"

    assert t_en.label == f"EN label uses ${{{new}}}"
    # With current signals, translation hint is unchanged
    assert t_en.hint == f"EN hint uses ${{{old}}}"

    # Dependencies still point to Q1's BaseQuestion
    assert root_question_2.relevant_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()
    assert root_question_2.constraint_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()
    assert root_question_2.choice_filter_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()
    assert root_question_2.calculation_dependencies.filter(
        pk=root_question_1.base_question.id
    ).exists()


@pytest.mark.django_db
def test_rename_does_not_touch_non_token_substrings(root_question_1, root_question_2):
    """
    Plain text occurrences of the old name must not change (only ${OldName} tokens are replaced).
    """
    old = root_question_2.name
    new = f"{old}_NEW"

    root_question_1.label = f"hello {old} world"
    if hasattr(root_question_1, "hint"):
        root_question_1.hint = f"just {old} text"
    root_question_1.save()

    root_question_2.name = new
    root_question_2.save()

    root_question_1.refresh_from_db()

    assert root_question_1.label == f"hello {old} world"
    if hasattr(root_question_1, "hint"):
        assert root_question_1.hint == f"just {old} text"


@pytest.mark.django_db
def test_regex_does_not_replace_similar_names(root_question_1, root_question_2):
    """
    Only exact ${OldName} tokens change; similar plain substrings remain.
    """
    old = root_question_2.name
    new = f"{old}_NEW"

    root_question_1.label = (
        f"token=${{{old}}} | no_token=prefix{old} suffix | also {old}X"
    )
    root_question_1.save()

    root_question_2.name = new
    root_question_2.save()

    root_question_1.refresh_from_db()

    assert f"${{{new}}}" in root_question_1.label
    assert f"prefix{old} suffix" in root_question_1.label
    assert f"{old}X" in root_question_1.label
    assert f"${{{old}}}" not in root_question_1.label


@pytest.mark.django_db
def test_case_only_root_question_rename_updates_tokens_and_subquestion_names(
    root_question_1, root_question_2, sub_question_1, suffix_1
):
    old = root_question_1.name
    new = old.lower()

    root_question_2.relevant = f"${{{old}}} > 10"
    root_question_2.save()
    root_question_2.relevant_dependencies.set([root_question_1.base_question])

    root_question_1.name = new
    root_question_1.save()

    root_question_2.refresh_from_db()
    sub_question_1.refresh_from_db()

    assert root_question_2.relevant == f"${{{new}}} > 10"
    assert sub_question_1.name == f"{new}{suffix_1.name}"


class TestCaseInsensitiveRootQuestionRenameSignals(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Signals Org")
        module = Module.objects.create(name="SignalsModule", label="Signals Module")
        module.organizations.add(organization)
        self.submodule = Submodule.objects.create(
            name="SignalsSubmodule",
            label="Signals Submodule",
            module=module,
            appearance="test",
        )
        self.root_question_1 = RootQuestion.objects.create(
            name="TestQuestion1",
            label="Test Question 1",
            type=QuestionType.INTEGER,
            appearance="test",
        )
        self.root_question_1.submodule.add(self.submodule)
        self.root_question_2 = RootQuestion.objects.create(
            name="TestQuestion2",
            label="Test Question 2",
            type=QuestionType.INTEGER,
            appearance="test",
        )
        self.root_question_2.submodule.add(self.submodule)
        self.suffix = Suffix.objects.create(
            name="Suffix1",
            description="Suffix 1",
            type=QuestionType.TEXT,
        )
        self.sub_question = SubQuestion.objects.create(
            root_question=self.root_question_1,
            suffix=self.suffix,
            label="SubQuestion 1",
        )

    def test_case_only_rename_updates_tokens_and_subquestion_names(self):
        old = self.root_question_1.name
        new = old.lower()

        self.root_question_2.relevant = f"${{{old}}} > 10"
        self.root_question_2.save()
        self.root_question_2.relevant_dependencies.set(
            [self.root_question_1.base_question]
        )

        self.root_question_1.name = new
        self.root_question_1.save()

        self.root_question_2.refresh_from_db()
        self.sub_question.refresh_from_db()

        self.assertEqual(self.root_question_2.relevant, f"${{{new}}} > 10")
        self.assertEqual(self.sub_question.name, f"{new}{self.suffix.name}")
