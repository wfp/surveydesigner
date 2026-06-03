import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from questions.views import (
    ConstraintCreateView,
    RelevantCreateView,
    UploadQuestionsView,
)


def test_relevant_create_view_get(logged_admin_client):
    response = logged_admin_client.get("/admin/questions/relevant/")
    assert response.status_code == 200


def test_upload_questions_view_get(logged_admin_client):
    response = logged_admin_client.get("/admin/questions/import/")
    assert response.status_code == 200


def test_upload_questions_view_post(logged_admin_client):
    with open(
        "./survey_designer/apps/questions/tests/files/questions.xlsx", "rb"
    ) as file:
        response = logged_admin_client.post(
            "/admin/questions/import/", {"file": file}, follow=True
        )
        assert response.status_code == 200


def test_base_question_autocomplete_term_search(logged_admin_client, root_question_1):
    search_term = root_question_1.name[:5].lower()
    response = logged_admin_client.get(
        f"/admin/questions/basequestion/autocomplete/?term={search_term}"
    )
    assert response.status_code == 200
    assert root_question_1.name in response.content.decode()


def test_base_question_autocomplete_q_search(logged_admin_client, root_question_1):
    search_term = root_question_1.name[:5].lower()
    response = logged_admin_client.get(
        f"/admin/questions/basequestion/autocomplete/?q={search_term}"
    )
    assert response.status_code == 200
    assert root_question_1.name in response.content.decode()


def test_repeat_section_autocomplete_search(logged_admin_client, repeat_section_1):
    search_term = repeat_section_1.name[:5].lower()
    response = logged_admin_client.get(
        f"/api/repeat-section-autocomplete/?q={search_term}"
    )
    assert response.status_code == 200
    assert repeat_section_1.name in response.content.decode()


def test_indicator_autocomplete_search(logged_admin_client, indicator_1):
    search_term = indicator_1.name[:5].lower()
    response = logged_admin_client.get(f"/api/indicator-autocomplete/?q={search_term}")
    assert response.status_code == 200
    assert indicator_1.name in response.content.decode()


def test_language_autocomplete_returns_select2_results(logged_admin_client):
    response = logged_admin_client.get("/api/language-autocomplete/")
    assert response.status_code == 200

    results = response.json()["results"]
    assert {"id": "en", "text": "English"} not in results
    assert {"id": "fr", "text": "French"} in results


def test_language_autocomplete_filters_by_code_and_label(logged_admin_client):
    response = logged_admin_client.get("/api/language-autocomplete/?q=fr")
    assert response.status_code == 200
    assert response.json()["results"] == [{"id": "fr", "text": "French"}]

    response = logged_admin_client.get("/api/language-autocomplete/?q=span")
    assert response.status_code == 200
    assert response.json()["results"] == [{"id": "es", "text": "Spanish"}]


class TestConstraintCreateView:
    @pytest.mark.django_db
    def test_initial_form_data(self, logged_admin_client, root_question_1):
        base_question = root_question_1.base_question
        ids = f"{base_question.id}"

        response = logged_admin_client.get(reverse("constraint") + f"?ids={ids}")

        assert response.status_code == 200
        form = response.context["form"]
        assert "base_questions" in form.initial
        assert len(form.initial["base_questions"]) == 1
        assert form.initial["base_questions"][0] == base_question

    @pytest.mark.django_db
    def test_get_success_url(self):
        view = ConstraintCreateView()
        expected_url = reverse("admin:questions_basequestion_changelist")
        assert view.get_success_url() == expected_url

    def test_get_formset_class(self):
        view = ConstraintCreateView()
        formset_class = view.get_formset_class()
        assert formset_class.extra == 0
        assert formset_class.min_num == 1
        assert formset_class.validate_min

    def test_get_translation_formset_class(self):
        view = ConstraintCreateView()
        translation_formset_class = view.get_translation_formset_class()
        assert translation_formset_class.extra == 1

    def test_post_text_mode(self, logged_admin_client, root_question_1):
        formset2_data = {
            "translation-TOTAL_FORMS": "1",
            "translation-INITIAL_FORMS": "0",
            "translation-MIN_NUM_FORMS": "1",
            "translation-MAX_NUM_FORMS": "1000",
            "translation-0-language": "en",
            "translation-0-label": "label",
        }
        form_data = {
            "base_questions": [root_question_1.base_question.id],
            "mode": "text",
            "constraint": "random constraint",
            "constraint_message": "random constraint message",
        }
        response = logged_admin_client.post(
            reverse("constraint"),
            {**formset2_data, **form_data},
        )
        assert response.status_code == 302
        storage = get_messages(response.wsgi_request)
        messages = list(storage)
        assert len(messages) == 1
        assert str(messages[0]) == "Constraint successfully added."

    def test_post_form_mode(self, logged_admin_client, root_question_1):
        formset1_data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-question": "",
            "form-0-operator": "=",
            "form-0-reference_question": "SELF",
            "form-0-value": "10",
            "form-0-logical_operator": "",
        }
        formset2_data = {
            "translation-TOTAL_FORMS": "1",
            "translation-INITIAL_FORMS": "0",
            "translation-MIN_NUM_FORMS": "1",
            "translation-MAX_NUM_FORMS": "1000",
            "translation-0-language": "en",
            "translation-0-label": "label",
        }
        form_data = {
            "base_questions": [root_question_1.base_question.id],
            "mode": "form",
            "constraint": "",
            "constraint_message": "",
        }
        response = logged_admin_client.post(
            reverse("constraint"),
            {**formset1_data, **formset2_data, **form_data},
        )
        assert response.status_code == 302
        storage = get_messages(response.wsgi_request)
        messages = list(storage)
        assert len(messages) == 1
        assert str(messages[0]) == "Constraint successfully added."


class TestRelevantCreateView:
    @pytest.mark.django_db
    def test_initial_form_data(self, logged_admin_client, root_question_1):
        base_question = root_question_1.base_question
        ids = f"{base_question.id}"

        response = logged_admin_client.get(reverse("relevant") + f"?ids={ids}")

        assert response.status_code == 200
        form = response.context["form"]
        assert "base_questions" in form.initial
        assert len(form.initial["base_questions"]) == 1
        assert form.initial["base_questions"][0] == base_question

    @pytest.mark.django_db
    def test_get_success_url(self):
        view = RelevantCreateView()
        expected_url = reverse("admin:questions_basequestion_changelist")
        assert view.get_success_url() == expected_url

    @pytest.mark.django_db
    def test_post(self, logged_admin_client, root_question_1):
        form_data = {
            "base_questions": [root_question_1.base_question.id],
            "relevant": "relevant",
        }
        response = logged_admin_client.post(
            reverse("relevant"),
            form_data,
        )
        assert response.status_code == 302
        storage = get_messages(response.wsgi_request)
        messages = list(storage)
        assert len(messages) == 1
        assert str(messages[0]) == "Relevant formula successfully added."


class TestUploadQuestionsView:
    @pytest.mark.django_db
    def test_get_success_url(self, logged_admin_client):
        view = UploadQuestionsView()
        expected_url = reverse("admin:questions_basequestion_changelist")
        assert view.get_success_url() == expected_url

    @pytest.mark.django_db
    def test_get(self, logged_admin_client):
        response = logged_admin_client.get(reverse("import"))
        assert response.status_code == 200
