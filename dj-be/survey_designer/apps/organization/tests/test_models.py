import pytest
from django.core.exceptions import ValidationError
from organization.tests.factories import OrganizationFactory

pytestmark = pytest.mark.django_db


def test_allowed_domains_validation():
    OrganizationFactory(
        name="allowed_domain_test_organization",
        allowed_domains=["unique1.org", "non_unique.org"],
    )

    with pytest.raises(
        ValidationError,
        match=(
            "One of listed domains is already assigned to other organization. "
            "Domains should be unique across all organizations."
        ),
    ):
        OrganizationFactory(
            name="duplicated_domain_organization",
            allowed_domains=["unique2.org", "non_unique.org"],
        )
