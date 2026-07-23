import os
import shutil
import tempfile
import zipfile
from io import BytesIO

import factory
from accounts.tests.factories import UserFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from modules.factories import ModuleFactory, SubmoduleFactory
from organization.models import Organization
from questions.const import QuestionType
from questions.factories import RootQuestionFactory
from questions.models import ChoiceGroup, ChoiceGroupFile
from rest_framework import status
from rest_framework.test import APITestCase


class ChoiceGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChoiceGroup

    name = factory.Sequence(lambda n: f"choice_group_{n}")


class ChoiceGroupFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChoiceGroupFile

    name = factory.Sequence(lambda n: f"choice_file_{n}")


_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="survey_designer_zip_test_")


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    },
    MEDIA_ROOT=_TEST_MEDIA_ROOT,
)
class GenerateXLSZipTestCase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("v1:generate_xls_form")
        self.organization = Organization.objects.create(name="Zip test organization")
        self.client.credentials(
            HTTP_SURVEY_DESIGNER_ORGANIZATIONS=str(self.organization.pk)
        )

        self.module = ModuleFactory()
        self.module.organizations.add(self.organization)
        self.submodule = SubmoduleFactory(module=self.module)

        # Create a standard select_one question (no file)
        self.choice_group = ChoiceGroupFactory()
        self.q1 = RootQuestionFactory(
            submodules=[{"submodule_id": self.submodule.id}],
            type=QuestionType.SELECT_ONE,
            choices=self.choice_group,
            name="q1",
        )

        # Create a select_one_from_file question
        csv_content = b"name,label\n1,One\n2,Two"
        self.csv_file = SimpleUploadedFile(
            "choices.csv", csv_content, content_type="text/csv"
        )
        self.choice_file = ChoiceGroupFileFactory(csv_file=self.csv_file)

        self.q2 = RootQuestionFactory(
            submodules=[{"submodule_id": self.submodule.id}],
            type=QuestionType.SELECT_ONE_FROM_FILE,
            choices_file=self.choice_file,
            name="q2",
        )

    def test_generate_standard_xls(self):
        """Test that a survey with NO external files returns an XLSX."""
        # Override setup for clean separation
        # Create clean module/submodule with only standard question
        module_clean = ModuleFactory()
        module_clean.organizations.add(self.organization)
        submodule_clean = SubmoduleFactory(module=module_clean)
        RootQuestionFactory(
            submodules=[{"submodule_id": submodule_clean.id}],
            type=QuestionType.SELECT_ONE,
            choices=ChoiceGroupFactory(),
            name="q_clean",
        )

        payload_clean = {
            "name": "Standard Survey",
            "submodules": [submodule_clean.id],
            "sub_questions": [],
            "submodules_order": [submodule_clean.id],
            "languages": [],
        }

        response = self.client.post(self.url, payload_clean, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("survey.xlsx", response["Content-Disposition"])

    def test_generate_zip_with_external_file(self):
        """Test that a survey WITH external files returns a ZIP."""
        payload = {
            "name": "File Survey",
            "submodules": [self.submodule.id],  # Contains q2 (file-based)
            "sub_questions": [],
            "submodules_order": [self.submodule.id],
            "languages": [],
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Validation Error: {response.content}",
        )
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("survey.zip", response["Content-Disposition"])

        buffer = BytesIO(response.content)
        self.choice_file.refresh_from_db()
        expected_filename = os.path.basename(self.choice_file.csv_file.name)

        with zipfile.ZipFile(buffer, "r") as z:
            namelist = z.namelist()
            self.assertIn("survey.xlsx", namelist)
            self.assertIn(expected_filename, namelist)

            # verify existing content
            csv_content = z.read(expected_filename)
            self.assertEqual(csv_content, b"name,label\n1,One\n2,Two")
