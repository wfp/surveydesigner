import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from questions.forms import ChoiceGroupFileAdminModelForm
from questions.models import ChoiceGroupFile

MIB = 1024 * 1024


def _upload(size):
    upload = SimpleUploadedFile("choices.csv", b"name,label\na,Choice A\n")
    # Exercise the upload-size checks without allocating a large file per case.
    upload.size = size
    return upload


@pytest.mark.django_db
@pytest.mark.parametrize("size", [10 * MIB + 1, 40 * MIB])
def test_default_limit_accepts_larger_uploads_in_admin_and_model(size):
    assert settings.EXTERNAL_CHOICE_FILE_MAX_BYTES == 40 * MIB
    form = ChoiceGroupFileAdminModelForm(
        data={"name": "size_test"}, files={"csv_file": _upload(size)}
    )
    assert form.is_valid(), form.errors
    ChoiceGroupFile(name="size_test", csv_file=_upload(size)).clean()


@pytest.mark.django_db
@pytest.mark.parametrize("limit", [40 * MIB, 1 * MIB])
def test_admin_and_model_reject_uploads_over_the_configured_limit(limit):
    with override_settings(EXTERNAL_CHOICE_FILE_MAX_BYTES=limit):
        form = ChoiceGroupFileAdminModelForm(
            data={"name": "size_test"}, files={"csv_file": _upload(limit + 1)}
        )
        assert not form.is_valid()
        assert f"{limit / MIB:g}MB" in str(form.errors)
        with pytest.raises(ValidationError, match=f"{limit / MIB:g}MB"):
            ChoiceGroupFile(name="size_test", csv_file=_upload(limit + 1)).clean()
