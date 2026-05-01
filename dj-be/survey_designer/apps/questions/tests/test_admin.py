import json

from accounts.const import PermissionGroups
from core.permissions import AdminPermissions
from core.utils import get_model_admin_base_url
from django.contrib import admin as django_admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.admin import AdminSite
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from lxml import html
from modules.models import Module, Submodule
from questions.admin import RepeatSectionAdmin, RootQuestionTranslationInline
from questions.const import QuestionType
from questions.models import (
    BaseQuestion,
    Calculation,
    ChoiceGroup,
    ChoiceGroupFile,
    RecallPeriod,
    RepeatSection,
    RootQuestion,
    SubQuestion,
    SubQuestionProxy,
    Suffix,
)
from surveys.models import SurveyCategory, SurveyType


def _build_repeat_section_admin():
    return RepeatSectionAdmin(RepeatSection, AdminSite())


def _assert_admin_search_works(logged_admin_client, model, expected_text):
    response = logged_admin_client.get(
        get_model_admin_base_url(model, "_changelist"),
        {"q": expected_text[:5].lower()},
    )
    assert response.status_code == 200
    assert expected_text in response.content.decode()


def _create_non_global_admin(organization):
    group, _ = Group.objects.get_or_create(name=PermissionGroups.ADMINS)
    AdminPermissions().set_permissions(group)
    user = get_user_model().objects.create_user(
        email=f"org-admin-{organization.id}@example.invalid",
        password="password",
        is_staff=True,
    )
    user.organization = organization
    user.save()
    user.groups.add(group)
    return user


def _create_root_question_for_org(organization, name):
    module = Module.objects.create(
        name=f"{name}Module",
        label=f"{name} Module",
    )
    module.organizations.add(organization)
    submodule = Submodule.objects.create(
        module=module,
        name=f"{name}Submodule",
        label=f"{name} Submodule",
    )
    question = RootQuestion.objects.create(
        name=name,
        label=f"{name} label",
        type=QuestionType.INTEGER,
    )
    question.submodule.add(submodule)
    return question


def _create_survey_type_for_org(organization, name):
    category = SurveyCategory.objects.create(
        name=f"{name}Category",
        label=f"{name} Category",
        order=1,
    )
    category.organizations.add(organization)
    survey_type = SurveyType.objects.create(
        category=category,
        name=name,
        label=f"{name} label",
        order=10,
    )
    survey_type.organizations.add(organization)
    return survey_type


def _build_root_question_translation_form(*, data=None, instance=None):
    class TestRootQuestionTranslationForm(RootQuestionTranslationInline.form):
        class Meta(RootQuestionTranslationInline.form.Meta):
            model = RootQuestionTranslationInline.model

    return TestRootQuestionTranslationForm(data=data, instance=instance)


def _create_choice_group_file_question_set(submodule):
    target_file = ChoiceGroupFile.objects.create(
        name="ChoiceFileTarget",
        csv_file=SimpleUploadedFile(
            "choice_file_target.csv",
            b"name,label\none,One\n",
            content_type="text/csv",
        ),
    )
    other_file = ChoiceGroupFile.objects.create(
        name="ChoiceFileOther",
        csv_file=SimpleUploadedFile(
            "choice_file_other.csv",
            b"name,label\ntwo,Two\n",
            content_type="text/csv",
        ),
    )

    root_match = RootQuestion.objects.create(
        name="ChoiceFileRootMatch",
        label="Choice File Root Match",
        type=QuestionType.SELECT_ONE_FROM_FILE,
        choices_file=target_file,
    )
    root_match.submodule.add(submodule)

    root_other = RootQuestion.objects.create(
        name="ChoiceFileRootOther",
        label="Choice File Root Other",
        type=QuestionType.SELECT_ONE_FROM_FILE,
        choices_file=other_file,
    )
    root_other.submodule.add(submodule)

    neutral_root = RootQuestion.objects.create(
        name="ChoiceFileNeutralRoot",
        label="Choice File Neutral Root",
        type=QuestionType.INTEGER,
    )
    neutral_root.submodule.add(submodule)

    match_suffix = Suffix.objects.create(
        name="ChoiceFileMatchSuffix",
        description="Choice file match suffix",
        type=QuestionType.SELECT_ONE_FROM_FILE,
        choices_file=target_file,
    )
    dual_suffix_1 = Suffix.objects.create(
        name="ChoiceFileDualSuffix1",
        description="Choice file dual suffix 1",
        type=QuestionType.SELECT_ONE_FROM_FILE,
        choices_file=target_file,
    )
    dual_suffix_2 = Suffix.objects.create(
        name="ChoiceFileDualSuffix2",
        description="Choice file dual suffix 2",
        type=QuestionType.SELECT_ONE_FROM_FILE,
        choices_file=target_file,
    )
    other_suffix = Suffix.objects.create(
        name="ChoiceFileOtherSuffix",
        description="Choice file other suffix",
        type=QuestionType.SELECT_ONE_FROM_FILE,
        choices_file=other_file,
    )

    sub_match = SubQuestion.objects.create(
        root_question=neutral_root,
        suffix=match_suffix,
        label="Choice File Match Question",
    )
    dual_match = SubQuestion.objects.create(
        root_question=neutral_root,
        suffix=dual_suffix_1,
        suffix_2=dual_suffix_2,
        label="Choice File Dual Match Question",
    )
    sub_other = SubQuestion.objects.create(
        root_question=neutral_root,
        suffix=other_suffix,
        label="Choice File Other Question",
    )

    return {
        "target_file": target_file,
        "root_match": root_match,
        "root_other": root_other,
        "sub_match": sub_match,
        "dual_match": dual_match,
        "sub_other": sub_other,
    }


def test_choice_group_admin_list_view(
    logged_admin_client,
    root_question_2,
    root_question_1,
    sub_question_1,
    sub_question_2,
    sub_question_3,
    sub_question_4,
):
    url = get_model_admin_base_url(ChoiceGroup, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_choice_group_admin_edit_view(logged_admin_client, choices_1, root_question_2):
    url = get_model_admin_base_url(ChoiceGroup, "_change", [choices_1.id])
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_choice_group_search_view(logged_admin_client, choices_1):
    _assert_admin_search_works(logged_admin_client, ChoiceGroup, choices_1.name)


def test_choice_group_file_search_view(logged_admin_client):
    choice_group_file = ChoiceGroupFile.objects.create(
        name="ChoiceGroupFileSearch",
        csv_file=SimpleUploadedFile(
            "choice_group_file_search.csv",
            b"name,label\none,One\n",
            content_type="text/csv",
        ),
    )
    _assert_admin_search_works(
        logged_admin_client, ChoiceGroupFile, choice_group_file.name
    )


def test_choice_group_file_list_view_links_question_count_to_filtered_questions(
    logged_admin_client, submodule_1
):
    question_set = _create_choice_group_file_question_set(submodule_1)

    response = logged_admin_client.get(
        get_model_admin_base_url(ChoiceGroupFile, "_changelist")
    )

    assert response.status_code == 200

    tree = html.fromstring(response.content)
    row = next(
        row
        for row in tree.xpath("//tr")
        if question_set["target_file"].name in row.text_content()
    )
    button = row.xpath(".//button")[0]
    onclick = button.get("onclick") or button.get("onClick") or ""

    assert button.text_content().strip() == "3"
    assert get_model_admin_base_url(BaseQuestion, "_changelist") in onclick
    assert f"choice_file_filter={question_set['target_file'].id}" in onclick


def test_base_questions_list_view(logged_admin_client, xls_form_data):
    url = get_model_admin_base_url(BaseQuestion, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_base_questions_list_view_filters_by_choice_group_file(
    logged_admin_client, submodule_1
):
    question_set = _create_choice_group_file_question_set(submodule_1)

    url = (
        get_model_admin_base_url(BaseQuestion, "_changelist")
        + f"?choice_file_filter={question_set['target_file'].id}"
    )
    response = logged_admin_client.get(url)

    assert response.status_code == 200

    tree = html.fromstring(response.content)
    rows_text = "\n".join(row.text_content().strip() for row in tree.xpath("//tr"))

    assert question_set["root_match"].name in rows_text
    assert question_set["sub_match"].name in rows_text
    assert question_set["dual_match"].name in rows_text
    assert question_set["root_other"].name not in rows_text
    assert question_set["sub_other"].name not in rows_text


def test_base_questions_search_view(logged_admin_client, root_question_1):
    search_term = root_question_1.name[:5].lower()
    url = get_model_admin_base_url(BaseQuestion, "_changelist") + f"?q={search_term}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert root_question_1.name in response.content.decode()


def test_non_global_admin_cannot_duplicate_other_org_question(
    django_client, organization_1, organization_2
):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    question = _create_root_question_for_org(organization_2, "OtherOrgActionQuestion")

    response = django_client.post(
        reverse("admin:questions_basequestion_changelist"),
        {
            "action": "duplicate",
            "index": "0",
            ACTION_CHECKBOX_NAME: [str(question.base_question.id)],
        },
        follow=True,
    )

    assert response.status_code == 200
    assert (
        "Action not allowed for objects outside your organization"
        in response.content.decode()
    )
    assert not RootQuestion.objects.filter(name="OtherOrgActionQuestion_1").exists()


def test_non_global_admin_can_duplicate_own_org_question(django_client, organization_1):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    question = _create_root_question_for_org(organization_1, "OwnOrgActionQuestion")

    response = django_client.post(
        reverse("admin:questions_basequestion_changelist"),
        {
            "action": "duplicate",
            "index": "0",
            ACTION_CHECKBOX_NAME: [str(question.base_question.id)],
        },
    )

    assert response.status_code == 302
    assert RootQuestion.objects.filter(name="OwnOrgActionQuestion_1").exists()


def test_non_global_admin_cannot_sort_other_org_question(
    django_client, organization_1, organization_2
):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    question = _create_root_question_for_org(organization_2, "OtherOrgSortQuestion")
    question.base_question.order = 20
    question.base_question.save(update_fields=["order"])

    response = django_client.post(
        reverse("admin:questions_basequestion_sortable_update"),
        data=json.dumps({"updatedItems": [[question.base_question.id, 1]]}),
        content_type="application/json",
    )

    assert response.status_code == 403
    question.base_question.refresh_from_db()
    assert question.base_question.order == 20


def test_non_global_admin_cannot_sort_other_org_survey_type(
    django_client, organization_1, organization_2
):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    survey_type = _create_survey_type_for_org(organization_2, "OtherOrgSurveyType")

    response = django_client.post(
        reverse("admin:surveys_surveytype_sortable_update"),
        data=json.dumps({"updatedItems": [[survey_type.id, 1]]}),
        content_type="application/json",
    )

    assert response.status_code == 403
    survey_type.refresh_from_db()
    assert survey_type.order == 10


def test_non_global_admin_can_sort_own_org_question(django_client, organization_1):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    question = _create_root_question_for_org(organization_1, "OwnOrgSortQuestion")
    question.base_question.order = 20
    question.base_question.save(update_fields=["order"])

    response = django_client.post(
        reverse("admin:questions_basequestion_sortable_update"),
        data=json.dumps({"updatedItems": [[question.base_question.id, 1]]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    question.base_question.refresh_from_db()
    assert question.base_question.order == 1


def test_non_global_admin_can_sort_own_org_survey_type(django_client, organization_1):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    survey_type = _create_survey_type_for_org(organization_1, "OwnOrgSurveyType")

    response = django_client.post(
        reverse("admin:surveys_surveytype_sortable_update"),
        data=json.dumps({"updatedItems": [[survey_type.id, 1]]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    survey_type.refresh_from_db()
    assert survey_type.order == 1


def test_non_global_admin_only_gets_reorder_handle_for_changeable_rows(
    django_client, organization_1, organization_2
):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    own_survey_type = _create_survey_type_for_org(
        organization_1, "OwnOrgSurveyTypeHandle"
    )
    other_survey_type = _create_survey_type_for_org(
        organization_2, "OtherOrgSurveyTypeHandle"
    )

    response = django_client.get(reverse("admin:surveys_surveytype_changelist"))
    model_admin = django_admin.site._registry[SurveyType]
    model_admin.get_list_display(response.wsgi_request)
    model_admin.enable_sorting = True

    assert response.status_code == 200
    assert "_reorder_" in response.context["cl"].list_display
    assert "drag handle" in str(model_admin._reorder_(own_survey_type))
    assert "drag handle" not in str(model_admin._reorder_(other_survey_type))


def test_non_global_admin_cannot_directly_post_relevant_for_other_org_question(
    django_client, organization_1, organization_2
):
    user = _create_non_global_admin(organization_1)
    django_client.force_login(user)
    question = _create_root_question_for_org(organization_2, "OtherOrgRelevantQuestion")

    response = django_client.post(
        reverse("relevant"),
        {
            "base_questions": [str(question.base_question.id)],
            "relevant": "1 = 1",
        },
    )

    assert response.status_code == 200
    assert "You do not have permission to change" in response.content.decode()
    question.refresh_from_db()
    assert question.relevant == ""


def test_root_question_admin_edit_view(
    logged_admin_client,
    root_question_1,
    sub_question_1,
    sub_question_2,
    sub_question_3,
    sub_question_4,
):
    url = get_model_admin_base_url(RootQuestion, "_change", [root_question_1.id])
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_root_question_admin_add_view_uses_single_jquery_for_dal_widgets(
    logged_admin_client,
):
    url = get_model_admin_base_url(RootQuestion, "_add")
    response = logged_admin_client.get(url)
    assert response.status_code == 200

    content = response.content.decode()

    assert "/static/admin/js/vendor/jquery/jquery.js" in content
    assert "/static/admin/js/vendor/jquery/jquery.min.js" not in content
    assert "/static/js/admin/jquery-bridge.js" in content
    assert "/static/autocomplete_light/autocomplete_light.js" in content
    assert "data-autocomplete-light-function=select2" in content
    assert "id=id_repeat_sections" in content
    assert "id=id_indicators" in content


def test_translation_form_language_widget_renders_language_options():
    form = _build_root_question_translation_form()

    language_select = html.fromstring(str(form["language"]))
    options = {
        option.get("value"): option.text
        for option in language_select.xpath(".//option")
    }

    assert "en" not in options
    assert options["fr"] == "French"
    assert options["es"] == "Spanish"


def test_translation_form_rejects_new_english_translation(root_question_1):
    form = _build_root_question_translation_form(
        data={
            "root_question": root_question_1.id,
            "language": "en",
            "label": "Duplicate English",
            "hint": "",
        }
    )

    assert not form.is_valid()
    assert "language" in form.errors


def test_translation_form_allows_existing_english_translation_row(root_question_1):
    translation = RootQuestionTranslationInline.model.objects.create(
        root_question=root_question_1,
        language="en",
        label="Existing English",
        hint="",
    )

    form = _build_root_question_translation_form(
        instance=translation,
        data={
            "root_question": root_question_1.id,
            "language": "en",
            "label": "Existing English Updated",
            "hint": "",
        },
    )

    assert form.is_valid(), form.errors


def test_recall_period_list_view(logged_admin_client, sub_question_2):
    url = get_model_admin_base_url(RecallPeriod, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_recall_period_search_view(logged_admin_client, recall_period_1):
    _assert_admin_search_works(logged_admin_client, RecallPeriod, recall_period_1.name)


def test_suffix_list_view(
    logged_admin_client, sub_question_1, sub_question_3, sub_question_4
):
    url = get_model_admin_base_url(Suffix, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_suffix_search_view(logged_admin_client, suffix_1):
    _assert_admin_search_works(logged_admin_client, Suffix, suffix_1.name)


def test_root_question_admin_edit_view_orders_sub_question_suffixes_alphabetically(
    logged_admin_client,
    root_question_1,
    sub_question_1,
    sub_question_2,
    sub_question_4,
):
    expected_names = ["_alpha", "_middle", "_zeta"]
    for suffix_name in ("_zeta", "_alpha", "_middle"):
        Suffix.objects.create(
            name=suffix_name,
            description=f"{suffix_name} description",
            type=QuestionType.TEXT,
        )

    response = logged_admin_client.get(
        get_model_admin_base_url(RootQuestion, "_change", [root_question_1.id])
    )

    assert response.status_code == 200

    tree = html.fromstring(response.content)
    suffix_select = next(
        select
        for select in tree.xpath("//select")
        if (select.get("id") or "").startswith("id_sub_questions-")
        and (select.get("id") or "").endswith("-suffix")
        and "__prefix__" not in (select.get("id") or "")
    )
    suffix_2_select = next(
        select
        for select in tree.xpath("//select")
        if (select.get("id") or "").startswith("id_sub_questions-")
        and (select.get("id") or "").endswith("-suffix_2")
        and "__prefix__" not in (select.get("id") or "")
    )

    suffix_names = [
        option.text_content().strip()
        for option in suffix_select.xpath("./option[@value!='']")
    ]
    suffix_2_names = [
        option.text_content().strip()
        for option in suffix_2_select.xpath("./option[@value!='']")
    ]

    assert [name for name in suffix_names if name in expected_names] == expected_names
    assert [name for name in suffix_2_names if name in expected_names] == expected_names


def test_repeat_section_list_view(logged_admin_client, repeat_section_1):
    url = get_model_admin_base_url(RepeatSection, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_repeat_section_search_view(logged_admin_client, repeat_section_1):
    _assert_admin_search_works(
        logged_admin_client, RepeatSection, repeat_section_1.name
    )


def test_repeat_section_questions_field_uses_autocomplete_widget(request_factory):
    repeat_section_admin = _build_repeat_section_admin()
    request = request_factory.get(reverse("admin:questions_repeatsection_add"))
    form = repeat_section_admin.get_form(request)()

    assert repeat_section_admin.autocomplete_fields == ("questions",)
    assert isinstance(form.fields["questions"].widget, AutocompleteSelectMultiple)


def test_sub_question_list_view(
    logged_admin_client,
    root_question_1,
    sub_question_1,
    sub_question_2,
    sub_question_3,
    sub_question_4,
):
    url = (
        get_model_admin_base_url(SubQuestion, "_changelist")
        + f"?root_question__pk={root_question_1.id}"
    )
    response = logged_admin_client.get(url)
    assert response.status_code == 200

    tree = html.fromstring(response.content)

    paginator = tree.xpath('//p[@class="paginator"]')
    # Check that the paginator contains the expected text
    assert paginator[0].text.strip() == "3 Questions"

    rows = tree.xpath("//tr")
    rows_text_content = [row.text_content().strip() for row in rows]

    # Check that each sub_question is present somewhere in the table
    # Also check that sub_question 3 is not present (not mapped to root_question_1)
    assert "SubQuestion 1" in "\n".join(rows_text_content)
    assert "SubQuestion 2" in "\n".join(rows_text_content)
    assert "SubQuestion 3" not in "\n".join(rows_text_content)
    assert "SubQuestion 4" in "\n".join(rows_text_content)


def test_sub_question_search_view(logged_admin_client, sub_question_1):
    _assert_admin_search_works(logged_admin_client, SubQuestion, sub_question_1.name)


def test_sub_question_proxy_add_view_sets_request_user_and_creates_subquestion(
    logged_admin_client, admin, root_question_1, suffix_1
):
    url = (
        get_model_admin_base_url(SubQuestionProxy, "_add")
        + f"?ids={root_question_1.id}&names={root_question_1.name}"
    )
    response = logged_admin_client.post(
        url,
        {
            "label": "6 months",
            "suffix": str(suffix_1.id),
            "root_question_ids": str(root_question_1.id),
            "translations-TOTAL_FORMS": 0,
            "translations-INITIAL_FORMS": 0,
        },
    )

    assert response.status_code == 302

    root_question_1.refresh_from_db()
    assert root_question_1.updated_by == admin

    sub_question = SubQuestion.objects.get(
        root_question=root_question_1,
        suffix=suffix_1,
        suffix_2__isnull=True,
        recall_period__isnull=True,
    )
    assert sub_question.label == "6 months"
    assert sub_question.created_by == admin
    assert sub_question.updated_by == admin


def test_root_question_list_view(
    logged_admin_client,
    root_question_1,
    sub_question_1,
    sub_question_2,
    sub_question_3,
    sub_question_4,
):
    url = get_model_admin_base_url(RootQuestion, "_changelist") + "?test="
    response = logged_admin_client.get(url, follow=True)
    assert response.status_code == 200


def test_root_question_search_view(logged_admin_client, root_question_1):
    search_term = root_question_1.name[:5].lower()
    url = get_model_admin_base_url(RootQuestion, "_changelist") + f"?q={search_term}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert root_question_1.name in response.content.decode()


def test_calculation_search_view(logged_admin_client, calculation_1):
    _assert_admin_search_works(logged_admin_client, Calculation, calculation_1.name)


def test_root_question_admin_edit_form_errors_in_equations(
    logged_admin_client,
    root_question_1,
    root_question_2,
    submodule_1,
):
    url = get_model_admin_base_url(RootQuestion, "_change", [root_question_1.id])
    # Fill out the form with valid data
    # account for inlines with TOTAL_FORMS, INITIAL_FORMS
    response = logged_admin_client.post(
        url,
        {
            "submodule": str(submodule_1.id),
            "name": "TestQuestion1",
            "description": "Test Question",
            "label": "Test Question",
            "type": "integer",
            "constraint": f"${{{root_question_2.name}}}=999",
            "relevant": f"${{{root_question_2.name}}}>123",
            "choice_filter": f"${{{root_question_2.name}}}",
            "calculation": f"${{{root_question_2.name}}}+111",
            "base_question-TOTAL_FORMS": 0,
            "base_question-INITIAL_FORMS": 0,
            "constraint_translations-TOTAL_FORMS": 0,
            "constraint_translations-INITIAL_FORMS": 0,
            "translations-TOTAL_FORMS": 0,
            "translations-INITIAL_FORMS": 0,
            "sub_questions-TOTAL_FORMS": 0,
            "sub_questions-INITIAL_FORMS": 0,
        },
    )
    # Assert successful POST redirects to changelist view
    assert response.status_code == 302
    # Reload the object from the database
    root_question_1.refresh_from_db()

    assert root_question_1.constraint == f"${{{root_question_2.name}}}=999"
    assert root_question_1.relevant == f"${{{root_question_2.name}}}>123"
    assert root_question_1.choice_filter == f"${{{root_question_2.name}}}"
    assert root_question_1.calculation == f"${{{root_question_2.name}}}+111"

    # Test pre/post save signals
    assert root_question_2.id in root_question_1.constraint_dependencies.values_list(
        "root_question__id", flat=True
    )
    assert root_question_2.id in root_question_1.relevant_dependencies.values_list(
        "root_question__id", flat=True
    )
    assert root_question_2.id in root_question_1.choice_filter_dependencies.values_list(
        "root_question__id", flat=True
    )
    assert root_question_2.id in root_question_1.calculation_dependencies.values_list(
        "root_question__id", flat=True
    )

    # Fill out the form with invalid data
    response = logged_admin_client.post(
        url,
        {
            "constraint": "${nonexistent}=999",
            "relevant": "${nonexistent}=999",
            "choice_filter": "${nonexistent}=999",
            "calculation": "${nonexistent}=999",
        },
    )

    # Check that the form was not submitted successfully
    assert response.status_code == 200
    decoded_content = response.content.decode()
    assert "Invalid constraint - Questions not found: nonexistent" in decoded_content
    assert "Invalid relevant - Questions not found: nonexistent" in decoded_content


def test_root_question_admin_edit_passes_with_no_question_names_in_equations(
    logged_admin_client,
    root_question_1,
    submodule_1,
):
    # Test that the root question is saves without error when passing a constraint,
    # relevant that does not contain a question name

    url = get_model_admin_base_url(RootQuestion, "_change", [root_question_1.id])
    response = logged_admin_client.post(
        url,
        {
            "submodule": str(submodule_1.id),
            "name": "TestQuestion1",
            "description": "Test Question",
            "label": "Test Question",
            "type": "integer",
            "constraint": ". >= 0",
            "relevant": ". >= 1",
            "choice_filter": ". >= 2",
            "calculation": ". >= 3",
            "base_question-TOTAL_FORMS": 0,
            "base_question-INITIAL_FORMS": 0,
            "constraint_translations-TOTAL_FORMS": 0,
            "constraint_translations-INITIAL_FORMS": 0,
            "translations-TOTAL_FORMS": 0,
            "translations-INITIAL_FORMS": 0,
            "sub_questions-TOTAL_FORMS": 0,
            "sub_questions-INITIAL_FORMS": 0,
        },
    )
    assert response.status_code == 302
    root_question_1.refresh_from_db()

    assert root_question_1.constraint == ". >= 0"
    assert root_question_1.relevant == ". >= 1"
    assert root_question_1.choice_filter == ". >= 2"
    assert root_question_1.calculation == ". >= 3"


def test_choice_group_edit_is_active_choices(logged_admin_client, choices_1):
    url = get_model_admin_base_url(ChoiceGroup, "_change", [choices_1.id])
    choice_1 = choices_1.choices.get(name="1")
    choice_2 = choices_1.choices.get(name="2")

    # Test data with both choices set to active
    form_data_both_active = {
        "name": "Updated Name",
        "choices-TOTAL_FORMS": "2",
        "choices-INITIAL_FORMS": "2",
        "choices-MAX_NUM_FORMS": "",
        "choices-0-id": choice_1.id,
        "choices-0-choice_group": choices_1.id,
        "choices-0-is_active": "on",
        "choices-1-id": choice_2.id,
        "choices-1-choice_group": choices_1.id,
        "choices-1-is_active": "on",
    }
    response_both_active = logged_admin_client.post(url, form_data_both_active)
    assert response_both_active.status_code == 200

    content = response_both_active.content.decode("utf-8")

    assert "At least one choice must be active." not in content
    del form_data_both_active["choices-0-is_active"]
    del form_data_both_active["choices-1-is_active"]

    response_none_active = logged_admin_client.post(url, form_data_both_active)
    assert response_none_active.status_code == 200

    content = response_none_active.content.decode("utf-8")
    assert "At least one choice must be active." in content


def test_choice_group_admin_rejects_duplicate_and_invalid_order(
    logged_admin_client, choices_1
):
    choice1 = choices_1.choices.get(name="1")
    choice2 = choices_1.choices.get(name="2")

    # Both set to the same order (duplicate)
    form_data_dup = {
        "name": "Test Group",
        "choices-TOTAL_FORMS": "2",
        "choices-INITIAL_FORMS": "2",
        "choices-MAX_NUM_FORMS": "",
        "choices-0-id": choice1.id,
        "choices-0-choice_group": choices_1.id,
        "choices-0-is_active": "on",
        "choices-0-order": "1",
        "choices-1-id": choice2.id,
        "choices-1-choice_group": choices_1.id,
        "choices-1-is_active": "on",
        "choices-1-order": "1",  # Duplicate!
    }
    url = get_model_admin_base_url(ChoiceGroup, "_change", [choices_1.id])
    response = logged_admin_client.post(url, form_data_dup)
    content = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Duplicate order value: 1" in content or "already exists" in content

    # One set to zero (invalid)
    form_data_zero = dict(form_data_dup)
    form_data_zero["choices-0-order"] = "0"
    form_data_zero["choices-1-order"] = "2"
    response = logged_admin_client.post(url, form_data_zero)
    content = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Order must be a positive integer" in content

    # One set to negative (invalid)
    form_data_neg = dict(form_data_dup)
    form_data_neg["choices-0-order"] = "-2"
    form_data_neg["choices-1-order"] = "3"
    response = logged_admin_client.post(url, form_data_neg)
    content = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Order must be a positive integer" in content
