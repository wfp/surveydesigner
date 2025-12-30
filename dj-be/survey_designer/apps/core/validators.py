import re

from django.core.exceptions import ValidationError


def validate_name(value):
    if value[0].isdigit():
        raise ValidationError("Cannot start with a number")

    pattern = r"^\w+\_*$"

    if not re.match(pattern, value):
        raise ValidationError(
            "Cannot include special characters (except for '_'). Cannot include white spaces."
        )


def validate_names(value):
    names = value.split(", ")
    for name in names:
        validate_name(name)


# Provide aliases for old function names
validate_wfp_name = validate_name
validate_wfp_names = validate_names
