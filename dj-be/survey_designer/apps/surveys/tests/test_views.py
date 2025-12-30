def test_survey_api_view(
    api_client_authenticated_admin,
    survey_category_1,
    survey_category_2,
    survey_category_3,
    survey_type_1,
    survey_mode_1,
    survey_attribute_1,
    organization_1,
    organization_2,
):
    survey_category_1.organizations.add(organization_1)
    survey_category_2.organizations.add(organization_2)
    survey_category_3.organizations.add(organization_1, organization_2)
    survey_type_1.organizations.add(organization_1, organization_2)
    survey_mode_1.organizations.add(organization_1, organization_2)
    url = "/api/surveys/"
    api_client_authenticated_admin.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=f"{organization_1.id},{organization_2.id}"
    )
    response = api_client_authenticated_admin.get(url)
    assert response.status_code == 200
    assert len(response.data["categories"]) == 1
    assert response.data["categories"][0]["id"] == survey_category_3.id
    assert len(response.data["modes"]) == 1
    assert response.data["modes"][0]["id"] == survey_mode_1.id
    assert len(response.data["categories"][0]["survey_types"]) == 0
