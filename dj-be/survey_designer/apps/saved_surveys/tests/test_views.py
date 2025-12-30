from saved_surveys.models import SavedSurvey, SubQuestionSubmodule


class TestSavedSurveyApi:
    def test_get_saved_surveys(
        self, api_client_authenticated_admin, submodule_1, submodule_2, saved_survey_1
    ):
        url = "/api/saved-surveys/"
        response = api_client_authenticated_admin.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["id"] == saved_survey_1.id
        assert response.data[0]["submodules_order"] == [submodule_2.id, submodule_1.id]

    def test_create_saved_survey(
        self,
        api_client_authenticated_admin,
        survey_category_1,
        survey_type_1,
        survey_mode_1,
        survey_attribute_1,
        organization_1,
        submodule_1,
        submodule_2,
        sub_question_1,
        sub_question_2,
    ):
        survey_category_1.organizations.add(organization_1)
        survey_category_1.save()
        url = "/api/saved-surveys/"
        data = {
            "name": "Test Survey",
            "survey_type": survey_type_1.id,
            "attributes": [],
            "survey_indicators": [],
            "survey_category": survey_category_1.id,
            "organizations": [organization_1.id],
            "submodules": [submodule_1.id],
            "submodules_order": [submodule_2.id, submodule_1.id],
            "subquestions": {submodule_1.id: [sub_question_1.id, sub_question_2.id]},
        }
        response = api_client_authenticated_admin.post(url, data=data, format="json")
        assert response.status_code == 201
        saved_survey = SavedSurvey.objects.first()
        assert saved_survey.name == "Test Survey"
        submodule_mapping = SubQuestionSubmodule.objects.filter(
            saved_survey=saved_survey.id
        )
        assert submodule_mapping.count() == 2

    def test_update_saved_survey(
        self,
        api_client_authenticated_admin,
        saved_survey_1,
        survey_category_1,
        organization_1,
        sub_question_1,
    ):
        survey_category_1.organizations.add(organization_1)
        survey_category_1.save()

        url = f"/api/saved-surveys/{saved_survey_1.uuid}/"
        data = {
            "name": "Test Survey",
            "subquestions": {saved_survey_1.submodules.first().id: [sub_question_1.id]},
        }
        response = api_client_authenticated_admin.patch(url, data=data, format="json")
        assert response.status_code == 200
        saved_survey_1.refresh_from_db()
        assert saved_survey_1.name == "Test Survey"

        # test put method
        data = {
            "name": "Test Survey 2",
            "survey_type": saved_survey_1.survey_type.id,
            "attributes": [],
            "survey_indicators": [],
            "survey_category": saved_survey_1.survey_category.id,
            "organizations": [organization_1.id],
            "submodules": [saved_survey_1.submodules.first().id],
        }
        response = api_client_authenticated_admin.put(url, data=data)
        assert response.status_code == 200

        saved_survey_1.refresh_from_db()
        assert saved_survey_1.name == "Test Survey 2"

    def test_delete_saved_survey(self, api_client_authenticated_admin, saved_survey_1):
        url = f"/api/saved-surveys/{saved_survey_1.uuid}/"
        response = api_client_authenticated_admin.delete(url)
        assert response.status_code == 204
        assert response.data is None
        assert SavedSurvey.objects.count() == 0

    def test_duplicate_saved_survey(
        self, api_client_authenticated, user, subquestion_submodule, saved_survey_1
    ):
        url = f"/api/saved-surveys/{saved_survey_1.uuid}/copy/"
        response = api_client_authenticated.get(url)
        assert response.status_code == 200
        assert response.json()["id"] != saved_survey_1.id
        assert response.json()["uuid"] != saved_survey_1.uuid
        assert response.json()["name"] == saved_survey_1.name
        assert response.json()["owner"] == user.id
        assert response.json()["survey_type"]["id"] == saved_survey_1.survey_type.id
        assert (
            response.json()["survey_category"]["id"]
            == saved_survey_1.survey_category.id
        )

        new_survey = SavedSurvey.objects.get(id=response.json()["id"])
        assert list(new_survey.submodules.all()) == list(
            saved_survey_1.submodules.all()
        )
        assert list(new_survey.organizations.all()) == list(
            saved_survey_1.organizations.all()
        )
        assert list(new_survey.attributes.all()) == list(
            saved_survey_1.attributes.all()
        )
        assert list(new_survey.attributes.all()) == list(new_survey.attributes.all())

        assert (
            new_survey.subquestions_submodules.count()
            == saved_survey_1.subquestions_submodules.count()
        )
        assert (
            new_survey.submodule_orders.count()
            == saved_survey_1.submodule_orders.count()
        )
