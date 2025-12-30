import pytest
from core.validators import validate_name
from django.core.exceptions import ValidationError


def test_validate_name():
    with pytest.raises(ValidationError):
        validate_name("1name")

    with pytest.raises(ValidationError):
        validate_name("name!")
