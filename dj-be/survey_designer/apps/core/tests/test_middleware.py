from unittest import mock

import pytest
from django.http import HttpRequest
from rest_framework.request import Request

from survey_designer.apps.core.middleware import OrganizationMiddleware


@pytest.mark.parametrize(
    "header_content, expected_ids",
    [("1, 2, 4", [1, 2, 4]), ("", []), ("1, 2, 1, 2, 3, 1", [1, 2, 3])],
)
def test_organization_middleware(header_content, expected_ids):
    get_response = mock.MagicMock()
    middleware_instance = OrganizationMiddleware(get_response)
    request = HttpRequest()
    request.META = {
        "HTTP_SURVEY_DESIGNER_ORGANIZATIONS": header_content,
        "HTTP_DUMMY_HEADER": "123",
    }
    request = Request(request)
    middleware_instance(request)
    assert set(request.organization_ids) == set(expected_ids)
    assert request.organization_ids_parse_error is False


def test_organization_middleware_missing_header():
    get_response = mock.MagicMock()
    middleware_instance = OrganizationMiddleware(get_response)
    request = HttpRequest()
    request.META = {
        "HTTP_DUMMY_HEADER": "123",
    }
    request = Request(request)
    middleware_instance(request)
    assert set(request.organization_ids) == set()
    assert request.organization_ids_parse_error is False


def test_organization_middleware_malformed_header():
    get_response = mock.MagicMock()
    middleware_instance = OrganizationMiddleware(get_response)
    request = HttpRequest()
    request.META = {
        "HTTP_SURVEY_DESIGNER_ORGANIZATIONS": "1,invalid",
    }
    request = Request(request)

    middleware_instance(request)

    assert request.organization_ids == []
    assert request.organization_ids_parse_error is True
