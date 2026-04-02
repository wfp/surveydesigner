import pytest
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType

from survey_designer.apps.core.utils import get_model_admin_base_url


def _assert_admin_search_works(logged_admin_client, model, expected_text):
    response = logged_admin_client.get(
        get_model_admin_base_url(model, "_changelist"),
        {"q": expected_text[:5].lower()},
    )
    assert response.status_code == 200
    assert expected_text in response.content.decode()


@pytest.mark.django_db
class TestSurveyCategoryAdmin:
    def test_survey_category_queryset(self, logged_admin_client, survey_category_1):
        url = get_model_admin_base_url(SurveyCategory, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_category in queryset:
            assert hasattr(survey_category, "organization_names")
            assert isinstance(survey_category.organization_names, list)
            assert len(survey_category.organization_names) > 0

    def test_survey_category_search_view(self, logged_admin_client, survey_category_1):
        _assert_admin_search_works(
            logged_admin_client, SurveyCategory, survey_category_1.name
        )


@pytest.mark.django_db
class TestSurveyModeAdmin:
    def test_survey_mode_queryset(self, logged_admin_client, survey_mode_1):
        url = get_model_admin_base_url(SurveyMode, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_mode in queryset:
            assert hasattr(survey_mode, "organization_names")
            assert isinstance(survey_mode.organization_names, list)
            assert len(survey_mode.organization_names) > 0

    def test_survey_mode_search_view(self, logged_admin_client, survey_mode_1):
        _assert_admin_search_works(logged_admin_client, SurveyMode, survey_mode_1.name)


@pytest.mark.django_db
class TestSurveyTypeAdmin:
    def test_survey_type_queryset(self, logged_admin_client, survey_type_1):
        url = get_model_admin_base_url(SurveyType, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_type in queryset:
            assert hasattr(survey_type, "organization_names")
            assert isinstance(survey_type.organization_names, list)
            assert len(survey_type.organization_names) > 0

    def test_survey_type_search_view(self, logged_admin_client, survey_type_1):
        _assert_admin_search_works(logged_admin_client, SurveyType, survey_type_1.name)


@pytest.mark.django_db
class TestSurveyAttributeAdmin:
    def test_survey_attribute_queryset(self, logged_admin_client, survey_attribute_1):
        url = get_model_admin_base_url(SurveyAttribute, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_attribute in queryset:
            assert hasattr(survey_attribute, "organization_names")
            assert isinstance(survey_attribute.organization_names, list)
            assert len(survey_attribute.organization_names) > 0

    def test_survey_attribute_search_view(
        self, logged_admin_client, survey_attribute_1
    ):
        _assert_admin_search_works(
            logged_admin_client, SurveyAttribute, survey_attribute_1.name
        )
