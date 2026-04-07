from core.utils import get_model_admin_base_url
from django.core.files.uploadedfile import SimpleUploadedFile
from lxml import html
from questions.admin import RootQuestionTranslationInline
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


def _assert_admin_search_works(logged_admin_client, model, expected_text):
    response = logged_admin_client.get(
        get_model_admin_base_url(model, "_changelist"),
        {"q": expected_text[:5].lower()},
    )
    assert response.status_code == 200
    assert expected_text in response.content.decode()


def _build_root_question_translation_form(*, data=None, instance=None):
    class TestRootQuestionTranslationForm(RootQuestionTranslationInline.form):
        class Meta(RootQuestionTranslationInline.form.Meta):
            model = RootQuestionTranslationInline.model

    return TestRootQuestionTranslationForm(data=data, instance=instance)


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


def test_base_questions_list_view(logged_admin_client, xls_form_data):
    url = get_model_admin_base_url(BaseQuestion, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_base_questions_search_view(logged_admin_client, root_question_1):
    search_term = root_question_1.name[:5].lower()
    url = get_model_admin_base_url(BaseQuestion, "_changelist") + f"?q={search_term}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert root_question_1.name in response.content.decode()


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
