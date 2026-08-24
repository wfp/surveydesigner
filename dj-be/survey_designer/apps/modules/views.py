import io
import json
import logging
import os
import uuid
import zipfile
from json import JSONDecodeError
from xml.etree import ElementTree as ET

import django_rq
import requests
from accounts.models import UserAPISiteAPITypes
from core.organization_scope import (
    filter_for_selected_organizations,
    get_selected_organization_ids,
    validate_scoped_ids,
)
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.files.base import ContentFile
from django.db.models import BooleanField, Count, OuterRef, Prefetch, Q, Subquery, Value
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from django_rq import job
from documents.models import Document
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from modules.models import (
    Indicator,
    IndicatorMappingSurveyAttribute,
    IndicatorMappingSurveyMode,
    IndicatorMappingSurveyType,
    Module,
    Submodule,
    SubmoduleMappingSurveyAttribute,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
    SubmoduleRequiredGroup,
)
from modules.serializers import (
    GenerateXLSFormSerializer,
    IndicatorSerializer,
    ModuleSerializer,
    SubmoduleWithQuestionsSerializer,
    UploadXLSFormSerializer,
)
from modules.services import SubmodulesOrderValidator
from organization.models import Organization
from questions.models import (
    BaseQuestion,
    Choice,
    RepeatSection,
    RootQuestion,
    SubQuestion,
)
from questions.services import (
    ArtifactInfrastructureError,
    ArtifactInputError,
    DocConversion,
    ValidationIssue,
    ValidationResult,
    ValidatorInfrastructureError,
    XLSForm,
    XMLConversion,
    build_generated_artifact,
    failed_validation_result,
    validate_generated_artifact,
)
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rq.exceptions import NoSuchJobError
from rq.job import Job
from surveys.models import Survey, SurveyType

logger = logging.getLogger(__name__)


@job("generate-doc")
def generate_docx(data, user):
    file_name = f"{uuid.uuid4()}.docx"
    xlsx_form = get_xlsx_from_data(data)
    languages = data.get("languages", [])

    file = DocConversion(xlsx_form, languages).run()

    doc_model = Document.objects.create(type="doc", created_by=user)
    doc_model.document.save(file_name, ContentFile(file.read()))
    doc_model.save()

    return doc_model.id


_VALIDATED_DATA_NOT_SET = object()


def get_xlsx_from_request(
    get_serializer, request, as_wb=False, validated_data=_VALIDATED_DATA_NOT_SET
):
    if validated_data is _VALIDATED_DATA_NOT_SET:
        serializer = get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        validate_generation_scope(request, data)
    else:
        data = validated_data
    return get_xlsx_from_data(data, as_wb=as_wb)


def _validation_issues_from_detail(detail, field=None):
    if isinstance(detail, dict):
        issues = []
        for key, value in detail.items():
            issues.extend(_validation_issues_from_detail(value, field=str(key)))
        return issues
    if isinstance(detail, (list, tuple)):
        issues = []
        for value in detail:
            issues.extend(_validation_issues_from_detail(value, field=field))
        return issues
    return [
        ValidationIssue(
            code="INPUT_INVALID",
            layer="composition",
            severity="error",
            message=str(detail),
            field=field,
        )
    ]


def prepare_validated_artifact(get_serializer, request):
    """Build and validate one exact artifact before an action has side effects."""

    try:
        serializer = get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        validate_generation_scope(request, data)
    except APIException as exc:
        result = ValidationResult(
            valid=False,
            errors=tuple(_validation_issues_from_detail(exc.detail)),
        )
        return None, None, result, status.HTTP_400_BAD_REQUEST

    try:
        # Passing validated_data keeps serializer and scope checks single-pass,
        # while retaining this helper's historical patch point in tests/callers.
        xlsx_form = get_xlsx_from_request(
            get_serializer, request, as_wb=True, validated_data=data
        )
        artifact = build_generated_artifact(xlsx_form)
    except ArtifactInputError as exc:
        return (
            data,
            None,
            failed_validation_result(exc.issue),
            status.HTTP_400_BAD_REQUEST,
        )
    except ArtifactInfrastructureError as exc:
        issue = ValidationIssue(
            code="ARTIFACT_UNAVAILABLE",
            layer="composition",
            severity="error",
            message=str(exc),
        )
        return (
            data,
            None,
            failed_validation_result(issue),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:
        issue = ValidationIssue(
            code="ARTIFACT_GENERATION_FAILED",
            layer="composition",
            severity="error",
            message=f"Unable to generate the survey artifact: {exc}",
        )
        return (
            data,
            None,
            failed_validation_result(issue),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        result = validate_generated_artifact(artifact, converter_cls=XMLConversion)
    except ValidatorInfrastructureError as exc:
        issue = ValidationIssue(
            code="VALIDATOR_UNAVAILABLE",
            layer="validator",
            severity="error",
            message=str(exc),
        )
        return (
            data,
            xlsx_form,
            failed_validation_result(issue, artifact_hash=artifact.artifact_hash),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:
        issue = ValidationIssue(
            code="VALIDATOR_FAILURE",
            layer="validator",
            severity="error",
            message=f"Survey validation could not complete: {exc}",
        )
        return (
            data,
            xlsx_form,
            failed_validation_result(issue, artifact_hash=artifact.artifact_hash),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return data, xlsx_form, result, status.HTTP_200_OK


def _validation_response(result, http_status):
    return Response(result.as_dict(), status=http_status)


def _validation_payload(result):
    return result.as_dict()


def _add_validation_headers(response, result):
    warnings = json.dumps(
        [warning.as_dict() for warning in result.warnings], separators=(",", ":")
    )
    response["X-Survey-Validation-Warnings"] = warnings
    # Keep a short generic alias for clients that do not use the product prefix.
    response["X-Validation-Warnings"] = warnings
    response["X-Survey-Artifact-Hash"] = result.artifact_hash
    return response


INDICATOR_ORGANIZATION_RELATIONS = (
    "questions__root_question__submodule__module__organizations",
    "questions__sub_question__root_question__submodule__module__organizations",
    "questions__repeat_section__submodule__module__organizations",
    "mapping__survey_types__organizations",
    "mapping__survey_attributes__organizations",
)


def validate_generation_scope(request, data):
    """Validate all submitted content before generation or other side effects."""
    organization_ids = get_selected_organization_ids(request)
    submodule_ids = set(data.get("submodules", [])) | set(
        data.get("submodules_order", [])
    )
    validate_scoped_ids(
        Submodule.objects.all(),
        submodule_ids,
        organization_ids,
        relations="module__organizations",
        field_name="submodules",
    )
    validate_scoped_ids(
        SubQuestion.objects.all(),
        data.get("sub_questions", []),
        organization_ids,
        relations="root_question__submodule__module__organizations",
        field_name="sub_questions",
    )
    validate_scoped_ids(
        Indicator.objects.all(),
        data.get("indicators", []),
        organization_ids,
        relations=INDICATOR_ORGANIZATION_RELATIONS,
        field_name="indicators",
    )
    survey_type = data.get("survey_type_id")
    validate_scoped_ids(
        SurveyType.objects.all(),
        [survey_type.pk] if survey_type else [],
        organization_ids,
        field_name="survey_type",
    )


def get_xlsx_from_data(data, as_wb=False):
    name = data.get("name", "")
    submodule_ids = data.get("submodules", [])
    submodules_order = data.get("submodules_order", {})
    sub_questions_ids = data.get("sub_questions", [])
    languages = data.get("languages", [])
    indicators = data.get("indicators", [])
    survey_type = data.get("survey_type_id", None)
    protected = survey_type.password_protected if survey_type else False

    xls_form = XLSForm(
        name=name,
        submodule_ids=submodule_ids,
        sub_question_ids=sub_questions_ids,
        submodules_order=submodules_order,
        languages=languages,
        indicators=indicators,
        protected=protected,
    )
    return xls_form.generate() if not as_wb else xls_form


upload_xls_form_response = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Preview response",
    examples=[
        OpenApiExample(
            name="Upload XLS Form response",
            media_type="application/json",
            value={"preview_url": ""},
        )
    ],
)


class UploadXLSForm(GenericAPIView):
    """
    Endpoint for generating XLS Form and uploading it to one of the external resources (MODA, KOBO)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UploadXLSFormSerializer

    def _get_response_error_details(self, response):
        try:
            return response.json()
        except (JSONDecodeError, ValueError):
            response_text = getattr(response, "text", "") or ""
            return {"response": response_text[:2000]}

    def _handle_bad_response(self, response, service_name, action):
        details = self._get_response_error_details(response)
        logger.warning(
            "%s publish failed while trying to %s. status=%s url=%s details=%s",
            service_name,
            action,
            response.status_code,
            getattr(response, "url", ""),
            details,
        )

        raise ValidationError(
            detail={
                "message": f"{service_name} rejected the survey while trying to {action}.",
                "details": details,
                "code": response.status_code,
                "service": service_name,
            }
        )

    def handle_kobo(self, url, artifact, token):
        name = artifact.form_name

        response = requests.post(
            f"{url}?format=json",
            data={"asset_type": "empty", "name": name, "settings": {}},
            headers={"Authorization": f"Token {token}"},
        )

        if not response.ok:
            self._handle_bad_response(response, "Kobo", "create the form asset")

        data = response.json()
        uid = data["uid"]

        upload_response = requests.post(
            "https://kobo.humanitarianresponse.info/api/v2/imports/",
            data={"assetUid": uid, "destination": data["url"], "name": name},
            files={"file": (f"{name}.xlsx", artifact.xlsx_bytes)},
            headers={"Authorization": f"Token {token}"},
        )

        if not upload_response.ok:
            self._handle_bad_response(
                upload_response, "Kobo", "import the generated XLSForm"
            )

        preview_url = f"https://kobo.humanitarianresponse.info/#/forms/{uid}/landing"

        return Response({"preview_url": preview_url})

    def handle_ona(self, site, url, artifact, token):
        response = requests.post(
            url,
            files={"xls_file": (f"{artifact.form_name}.xlsx", artifact.xlsx_bytes)},
            headers={"Authorization": f"Token {token}"},
        )

        if not response.ok:
            service_name = "Moda" if site.is_moda else "Ona"
            self._handle_bad_response(
                response, service_name, "upload the generated XLSForm"
            )

        data = response.json()

        response_payload = {
            "preview_url": data.get("enketo_preview_url", ""),
        }

        external_files = artifact.external_files
        if site.is_moda and external_files:
            uploaded_files = self._upload_moda_metadata(
                site, token, data, external_files
            )
            if uploaded_files:
                response_payload["metadata_uploaded_files"] = uploaded_files

        return Response(response_payload)

    def _upload_moda_metadata(self, site, token, submission_data, external_files):
        metadata_url = UserAPISiteAPITypes.get_metadata_url(site)
        if not metadata_url or not external_files:
            return []

        form_id = self._extract_moda_form_id(submission_data)
        if not form_id:
            raise ValidationError(
                {"message": "Unable to determine Moda form id for metadata upload."}
            )

        headers = {
            "Accept": "application/json",
            "Authorization": f"Token {token}",
        }
        uploaded_files = []

        for file_name, file_bytes in external_files.items():
            if not file_bytes:
                continue

            files = {
                "xform": (None, str(form_id)),
                "data_type": (None, "media"),
                "data_value": (None, file_name),
                "data_file": (file_name, io.BytesIO(file_bytes), "text/csv"),
            }
            response = requests.post(
                metadata_url,
                headers=headers,
                files=files,
            )

            if not response.ok:
                self._handle_moda_metadata_error(response, file_name)

            uploaded_files.append(file_name)

        return uploaded_files

    def _handle_moda_metadata_error(self, response, file_name):
        details = self._get_response_error_details(response)
        logger.warning(
            "Moda metadata upload failed. status=%s url=%s file=%s details=%s",
            response.status_code,
            getattr(response, "url", ""),
            file_name,
            details,
        )

        raise ValidationError(
            detail={
                "message": f"Failed to upload metadata file '{file_name}' to Moda.",
                "details": details,
                "code": response.status_code,
                "service": "Moda",
            }
        )

    @staticmethod
    def _extract_moda_form_id(submission_data):
        candidates = ("id", "formid_int", "form_id", "_id", "formid")
        for key in candidates:
            value = submission_data.get(key)
            if value:
                return str(value)

        url = submission_data.get("url", "")
        if url:
            form_id_candidate = url.rstrip("/").split("/")[-1]
            if form_id_candidate:
                return form_id_candidate

        return None

    @extend_schema(responses={200: upload_xls_form_response})
    def post(self, request, *args, **kwargs):
        data, _, validation, validation_status = prepare_validated_artifact(
            self.get_serializer, request
        )
        if not validation.valid:
            return _validation_response(validation, validation_status)

        artifact = validation.artifact

        api_key_id = data.get("id")
        project_id = data.get("project_id")

        api_configuration = self.request.user.api_keys.filter(id=api_key_id).first()
        if not api_configuration or not api_configuration.site:
            raise ValidationError(
                {
                    "message": "The selected publishing site is not configured.",
                    "details": {
                        "site": "Select a configured API key before publishing."
                    },
                }
            )
        site = api_configuration.site

        if site.is_ona and not project_id:
            return Response(
                {"message": "Project is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        url = UserAPISiteAPITypes.get_upload_url(site, project_id)

        if not url:
            raise ValidationError(
                {
                    "message": "The selected publishing site is not configured.",
                    "details": {
                        "site": "Select a configured API key before publishing."
                    },
                }
            )

        token = api_configuration.get_key()

        if site.is_kobo:
            response = self.handle_kobo(url, artifact, token)
            response.data.update(_validation_payload(validation))
            return response
        if site.is_ona:
            response = self.handle_ona(site, url, artifact, token)
            response.data.update(_validation_payload(validation))
            return response

        raise ValidationError({"message": "Site is not configured."})


generate_doc_form_response = OpenApiResponse(
    description=".docx file", response=OpenApiTypes.BINARY
)


class GenerateDocForm(GenericAPIView):
    """
    Endpoint for generating the Word Form that returns .docx file
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GenerateXLSFormSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        validate_generation_scope(request, data)
        user = request.user
        queue = django_rq.get_queue("generate-doc")
        job = queue.enqueue(generate_docx, data=data, user=user)

        return JsonResponse(
            {
                "jobId": job.id,
                "status": job.get_status(),
                "position": job.get_position(),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: generate_doc_form_response})
    def get(self, request, *args, **kwargs):
        try:
            job_id = request.GET.get("jobId")
            cancel_job = request.GET.get("cancelJob", False)
            redis_conn = django_rq.get_connection("generate-doc")
            job = Job.fetch(job_id, redis_conn)
        except NoSuchJobError:
            return JsonResponse(
                {"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return JsonResponse({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if cancel_job:
            try:
                job.cancel()
                return JsonResponse(
                    {"detail": "Job cancelled."}, status=status.HTTP_200_OK
                )
            except Exception as e:
                return JsonResponse(
                    {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                )

        doc = None
        if job.is_finished:
            try:
                doc_model = Document.objects.get(id=job.result)
                doc = doc_model.document.url
            except Exception as e:
                return JsonResponse(
                    {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                )

        return JsonResponse(
            {
                "doc": doc,
                "jobId": job.id,
                "status": job.get_status(),
                "position": job.get_position(),
            },
            status=status.HTTP_200_OK,
        )


generate_xls_form_response = OpenApiResponse(
    description=".xlsx file", response=OpenApiTypes.BINARY
)


class GenerateXLSForm(GenericAPIView):
    """
    Endpoint for generating XLS Form that returns .xlsx file
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GenerateXLSFormSerializer

    @extend_schema(responses={200: generate_xls_form_response})
    def post(self, request, *args, **kwargs):
        _, _, validation, validation_status = prepare_validated_artifact(
            self.get_serializer, request
        )
        if not validation.valid:
            # Even with responseType=blob, invalid artifacts are always JSON.
            return _validation_response(validation, validation_status)

        artifact = validation.artifact
        external_files = artifact.external_files
        if external_files:
            zip_buffer = io.BytesIO()
            try:
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.writestr("survey.xlsx", artifact.xlsx_bytes)
                    for filename, file_bytes in external_files.items():
                        zip_file.writestr(filename, file_bytes)
            except Exception as exc:
                issue = ValidationIssue(
                    code="ARTIFACT_SERIALIZATION_FAILURE",
                    layer="storage",
                    severity="error",
                    message=f"Unable to package the validated survey artifact: {exc}",
                )
                return _validation_response(
                    failed_validation_result(
                        issue, artifact_hash=validation.artifact_hash
                    ),
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type="application/zip",
            )
            response["Content-Disposition"] = "attachment; filename=survey.zip"
            return _add_validation_headers(response, validation)

        response = HttpResponse(
            artifact.xlsx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=survey.xlsx"
        return _add_validation_headers(response, validation)


class ValidateXLSForm(GenericAPIView):
    """Validate the exact generated artifact without storage or network effects."""

    serializer_class = GenerateXLSFormSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        _, _, validation, validation_status = prepare_validated_artifact(
            self.get_serializer, request
        )
        return _validation_response(validation, validation_status)


preview_xls_form_response = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description=".xlsx file",
    examples=[
        OpenApiExample(
            name="Preview XLS Form",
            media_type="application/json",
            value={
                "url": "url",
                "enketo_url": "enketo_url",
                "warnings": [],
                "errors": [],
            },
        )
    ],
)


class PreviewXLSForm(GenericAPIView):
    """
    Endpoint for previewing XLS Form using Enketo
    """

    serializer_class = GenerateXLSFormSerializer
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _read_file_content(file_obj):
        """
        Read file content regardless of whether we received a FieldFile or ContentFile.
        """
        if hasattr(file_obj, "open"):
            file_obj.open("rb")
            try:
                data = file_obj.read()
            finally:
                file_obj.close()
        else:
            data = file_obj.read()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        return data

    @extend_schema(responses={200: preview_xls_form_response})
    def post(self, request, *args, **kwargs):
        _, _, validation, validation_status = prepare_validated_artifact(
            self.get_serializer, request
        )
        if not validation.valid:
            return _validation_response(validation, validation_status)

        artifact = validation.artifact
        xml_data = artifact.xml

        url = ""
        enketo_url = ""
        external_files = artifact.external_files
        preview_id = uuid.uuid4().hex
        storage_prefix = os.path.join("previews", preview_id)

        try:
            survey = Survey.objects.create()
            storage = survey.file.storage

            file_url_map = {}
            for filename, file_bytes in external_files.items():
                storage_path = storage.save(
                    f"{storage_prefix}/{filename}", ContentFile(file_bytes)
                )
                file_url_map[filename] = storage.url(storage_path)

            xml_input = (
                xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data
            )
            root = ET.fromstring(xml_input)

            if file_url_map:
                ns = {
                    "xf": "http://www.w3.org/2002/xforms",
                    "h": "http://www.w3.org/1999/xhtml",
                }

                for instance in root.findall(".//xf:instance", namespaces=ns):
                    src = instance.get("src")
                    if src and src.startswith("jr://file-csv/"):
                        filename = src.split("/")[-1]
                        if filename in file_url_map:
                            instance.set("src", file_url_map[filename])

                for img in root.findall(".//h:img", namespaces=ns):
                    src = img.get("src")
                    if src and src.startswith("jr://images/"):
                        filename = src.split("/")[-1]
                        if filename in file_url_map:
                            img.set("src", file_url_map[filename])

                xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            else:
                xml_bytes = xml_input

            file_name = f"{storage_prefix}/form_preview.xml"
            survey.file.save(file_name, ContentFile(xml_bytes))
            url = survey.file.url
            enketo_url = survey.get_enketo_preview_url()
        except Exception as exc:
            issue = ValidationIssue(
                code="ARTIFACT_STORAGE_FAILURE",
                layer="storage",
                severity="error",
                message=f"Unable to store the validated preview artifact: {exc}",
            )
            return _validation_response(
                failed_validation_result(issue, artifact_hash=validation.artifact_hash),
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response = _validation_payload(validation)
        response.update(
            {
                "url": url,
                "enketo_url": enketo_url,
            }
        )
        return Response(response)


survey_type_param = OpenApiParameter(
    "type", description="SurveyType ID", type=OpenApiTypes.INT
)

survey_mode_param = OpenApiParameter(
    "mode", description="SurveyMode ID", type=OpenApiTypes.INT
)

survey_attributes_param = OpenApiParameter(
    "attributes",
    description="comma separated SurveyAttribute IDs",
    type=OpenApiTypes.STR,
)


@method_decorator(
    name="list",
    decorator=extend_schema(
        parameters=[
            survey_type_param,
            survey_mode_param,
            survey_attributes_param,
        ]
    ),
)
class ModuleViewSet(ModelViewSet):
    http_method_names = ["get"]
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 60, key_prefix="modules_"))  # Cache for 1 hour
    @method_decorator(vary_on_cookie)
    @method_decorator(vary_on_headers("Survey-Designer-Organizations", "Authorization"))
    def dispatch(self, *args, **kwargs):
        return super(ModelViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        organizations = get_selected_organization_ids(self.request)
        qs = filter_for_selected_organizations(super().get_queryset(), organizations)

        # Extract query parameters
        type_ = self.request.query_params.get("type")
        mode = self.request.query_params.get("mode")
        attributes = self.request.query_params.get("attributes")

        organizations_prefetch = Prefetch(
            "organizations", queryset=Organization.objects.all()
        )

        # Early return if all parameters are absent or empty
        if not any(
            [
                type_,
                mode,
                attributes and attributes.strip(),
            ]
        ):
            submodules_prefetch = Prefetch(
                "submodules",
                queryset=Submodule.objects.filter(root_questions__isnull=False)
                .prefetch_related("root_questions")
                .distinct(),
            )
            return qs.prefetch_related(
                submodules_prefetch, organizations_prefetch
            ).distinct()

        # Type filtering for submodules
        if type_:
            submodule_type_filter = Q(mapping__survey_types=type_)
        else:
            submodule_type_filter = Q()

        # Mode filtering for submodules
        if mode:
            submodule_mode_filter = Q(
                mapping__submodulemappingsurveytype__modes__survey_mode=mode
            )
        else:
            submodule_mode_filter = Q()

        # Attributes filtering
        if attributes and attributes.strip():
            # Attributes parameter is provided and not empty
            attributes_list = [
                int(attr_id) for attr_id in attributes.split(",") if attr_id.strip()
            ]
            # Include submodules with matching attributes or no attributes
            submodule_attributes_filter = Q(
                mapping__survey_attributes__in=attributes_list
            ) | Q(mapping__survey_attributes__isnull=True)
            # Exclude submodules with attributes not in the list
            submodule_attributes_exclude = Q(
                mapping__survey_attributes__isnull=False
            ) & ~Q(mapping__survey_attributes__in=attributes_list)
        else:
            # Include submodules with no attributes only
            submodule_attributes_filter = Q(mapping__survey_attributes__isnull=True)
            submodule_attributes_exclude = Q(mapping__survey_attributes__isnull=False)

        # Build submodule queryset
        submodule_queryset = (
            Submodule.objects.filter(root_questions__isnull=False)
            .filter(
                submodule_type_filter,
                submodule_mode_filter,
                submodule_attributes_filter,
            )
            .exclude(submodule_attributes_exclude)
            .distinct()
        )

        # Annotate with mandatory flags
        if type_:
            mandatory_type_sub_q = SubmoduleMappingSurveyType.objects.filter(
                submodule_mapping__submodule=OuterRef("id"),
                survey_type_id=type_,
                is_mandatory=True,
            ).values("is_mandatory")[:1]
            submodule_queryset = submodule_queryset.annotate(
                is_type_mandatory=Subquery(mandatory_type_sub_q)
            )
        else:
            submodule_queryset = submodule_queryset.annotate(
                is_type_mandatory=Value(False, output_field=BooleanField())
            )

        if mode:
            mandatory_mode_sub_q = SubmoduleMappingSurveyMode.objects.filter(
                survey_type__survey_type=type_,
                survey_type__submodule_mapping__submodule=OuterRef("id"),
                survey_mode_id=mode,
                is_mandatory=True,
            ).values("is_mandatory")[:1]
            submodule_queryset = submodule_queryset.annotate(
                is_mode_mandatory=Subquery(mandatory_mode_sub_q)
            )
        else:
            submodule_queryset = submodule_queryset.annotate(
                is_mode_mandatory=Value(False, output_field=BooleanField())
            )

        if attributes and attributes.strip():
            mandatory_attributes_sub_q = SubmoduleMappingSurveyAttribute.objects.filter(
                submodule_mapping__submodule=OuterRef("id"),
                survey_attribute_id__in=attributes_list,
                is_mandatory=True,
            ).values("is_mandatory")[:1]
            submodule_queryset = submodule_queryset.annotate(
                is_attributes_mandatory=Subquery(mandatory_attributes_sub_q)
            )
        else:
            submodule_queryset = submodule_queryset.annotate(
                is_attributes_mandatory=Value(False, output_field=BooleanField())
            )

        # Include mandatory submodules regardless of filters
        submodule_queryset = submodule_queryset.filter(
            Q(is_type_mandatory=True)
            | Q(is_mode_mandatory=True)
            | Q(is_attributes_mandatory=True)
            | (
                submodule_type_filter
                & submodule_mode_filter
                & submodule_attributes_filter
            )
        ).distinct()

        # Prefetch submodules
        submodules_prefetch = Prefetch(
            "submodules",
            queryset=submodule_queryset.prefetch_related("root_questions").distinct(),
        )

        # Build module queryset based on submodules in submodule_queryset
        module_queryset = qs.filter(submodules__in=submodule_queryset).distinct()

        return module_queryset.prefetch_related(
            submodules_prefetch, organizations_prefetch
        ).distinct()


submodule_ids_param = OpenApiParameter(
    "submodule_ids",
    description="comma separated Submodule IDs",
    type=OpenApiTypes.STR,
)
all_submodule_ids_param = OpenApiParameter(
    "all_submodule_ids",
    description="comma separated Submodule IDs",
    type=OpenApiTypes.STR,
)

indicator_ids_param = OpenApiParameter(
    "indicator_ids",
    description="comma separated Indicator IDs",
    type=OpenApiTypes.STR,
)


@method_decorator(
    name="list",
    decorator=extend_schema(parameters=[submodule_ids_param, indicator_ids_param]),
)
class SubmoduleViewSet(ModelViewSet):
    http_method_names = ["get"]
    queryset = Submodule.objects.all()
    serializer_class = SubmoduleWithQuestionsSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    @method_decorator(vary_on_cookie)
    @method_decorator(vary_on_headers("Survey-Designer-Organizations", "Authorization"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        submodule_ids = parse_int_list_param(
            self.request.query_params.get("submodule_ids", ""),
            "submodule_ids",
        )
        indicator_ids = parse_int_list_param(
            self.request.query_params.get("indicator_ids", ""),
            "indicator_ids",
        )
        submodule_ids_set = set()
        if submodule_ids:
            submodule_ids_set.update(submodule_ids)
        # get submodules related to indicators through BaseQuestion
        if indicator_ids:
            indicator_submodule_ids = (
                BaseQuestion.objects.filter(indicators__in=indicator_ids)
                .exclude(root_question__submodule=None)
                .values_list("root_question__submodule", flat=True)
                .distinct()
            )
            submodule_ids_set.update(set(indicator_submodule_ids))
        if submodule_ids_set:
            qs = qs.filter(id__in=submodule_ids_set)
        return qs

    def get_queryset(self):
        organizations = get_selected_organization_ids(self.request)
        qs = filter_for_selected_organizations(
            super().get_queryset(), organizations, relations="module__organizations"
        )

        sub_questions_prefetch = Prefetch(
            "sub_questions",
            queryset=SubQuestion.objects.all()
            .order_by()
            .select_related(
                "root_question",
                "root_question__choices",
                "root_question__choices_file",
                "suffix",
                "suffix__choices",
                "suffix__choices_file",
                "suffix_2",
                "suffix_2__choices",
                "suffix_2__choices_file",
                "recall_period",
            )
            .prefetch_related(
                "translations",
                Prefetch(
                    "root_question__choices__choices",
                    queryset=Choice.objects.order_by().prefetch_related("translations"),
                ),
                Prefetch(
                    "suffix__choices__choices",
                    queryset=Choice.objects.order_by().prefetch_related("translations"),
                ),
                Prefetch(
                    "suffix_2__choices__choices",
                    queryset=Choice.objects.order_by().prefetch_related("translations"),
                ),
            ),
        )

        root_questions_prefetch = Prefetch(
            "root_questions",
            queryset=RootQuestion.objects.select_related("choices", "choices_file")
            .prefetch_related(
                "translations",
                Prefetch(
                    "choices__choices",
                    queryset=Choice.objects.order_by().prefetch_related("translations"),
                ),
                sub_questions_prefetch,
            )
            .order_by(),
            to_attr="filtered_root_questions",
        )

        repeat_section_prefetch = Prefetch(
            "repeat_sections",
            queryset=RepeatSection.objects.prefetch_related("translations"),
        )

        required_groups_prefetch = Prefetch(
            "required_groups",
            queryset=SubmoduleRequiredGroup.objects.select_related(
                "required_suffix",
                "required_nested_suffix",
                "required_recall_period",
            ),
        )

        return qs.prefetch_related(
            root_questions_prefetch,
            repeat_section_prefetch,
            required_groups_prefetch,
        ).distinct()


examples = [
    OpenApiExample(
        "Example: submodule_ids=470,508",
        value=[
            "Combined (FCS/FCSN) contains questions from: Household Dietary Diversity Score (Combined FCS/FCSN/HDDS). Select only one of these submodules."
        ],
        response_only=True,
        description="An example response showing error messages for incompatible module combinations.",
    )
]


def parse_int_list_param(raw_value, param_name):
    values = raw_value.replace(",", " ").split()
    try:
        return [int(value) for value in values]
    except ValueError as exc:
        raise ValidationError(
            {param_name: "This parameter must contain only integers."}
        ) from exc


@extend_schema(
    parameters=[submodule_ids_param, indicator_ids_param, all_submodule_ids_param],
    responses={
        200: inline_serializer(
            name="SubmodulesOrderValidationResponse",
            fields={
                "messages": serializers.ListField(child=serializers.CharField()),
            },
        ),
    },
    examples=examples,
)
class SubmodulesOrderValidationView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 60))
    @method_decorator(vary_on_cookie)
    @method_decorator(vary_on_headers("Survey-Designer-Organizations", "Authorization"))
    def get(self, request, *args, **kwargs):
        organization_ids = get_selected_organization_ids(request)
        submodule_ids = parse_int_list_param(
            self.request.query_params.get("submodule_ids", ""),
            "submodule_ids",
        )
        indicator_ids = parse_int_list_param(
            self.request.query_params.get("indicator_ids", ""),
            "indicator_ids",
        )
        all_submodule_ids = parse_int_list_param(
            self.request.query_params.get("all_submodule_ids", ""),
            "all_submodule_ids",
        )
        validate_scoped_ids(
            Submodule.objects.all(),
            set(submodule_ids) | set(all_submodule_ids),
            organization_ids,
            relations="module__organizations",
            field_name="submodule_ids",
        )
        validate_scoped_ids(
            Indicator.objects.all(),
            indicator_ids,
            organization_ids,
            relations=INDICATOR_ORGANIZATION_RELATIONS,
            field_name="indicator_ids",
        )
        result = []

        if submodule_ids:
            validator = SubmodulesOrderValidator(
                submodule_ids, indicator_ids, all_submodule_ids
            )
            validator.process()
            result = validator.get_messages()

        return Response(result)


@method_decorator(
    name="list",
    decorator=extend_schema(
        parameters=[
            survey_type_param,
            survey_mode_param,
            survey_attributes_param,
        ]
    ),
)
class IndicatorViewSet(ModelViewSet):
    http_method_names = ["get"]
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    @method_decorator(vary_on_cookie)
    @method_decorator(vary_on_headers("Survey-Designer-Organizations", "Authorization"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        # 1) Build a “base” QuerySet with common annotations/prefetch
        organizations = get_selected_organization_ids(self.request)
        qs = (
            filter_for_selected_organizations(
                super().get_queryset(),
                organizations,
                relations=INDICATOR_ORGANIZATION_RELATIONS,
            )
            .annotate(
                question_count=Count("questions", distinct=True),
                root_question_ids=ArrayAgg(
                    "questions__root_question_id", distinct=True
                ),
            )
            .select_related("indicator_area")
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=BaseQuestion.objects.only(
                        "id", "root_question"
                    ).select_related("root_question"),
                )
            )
            .order_by("order")
        )

        # 2) Read query params
        type_ = self.request.query_params.get("type")
        mode_ = self.request.query_params.get("mode")
        attributes_ = self.request.query_params.get("attributes")

        # 3) If no type/mode, just filter out indicators with zero questions
        if not (type_ or mode_ or attributes_ and attributes_.strip()):
            return qs.filter(question_count__gt=0)

        # 4) Otherwise, define your type & mode subqueries/annotations
        if type_:
            indicator_type_filter = Q(mapping__survey_types=type_)
            mandatory_type_sub_q = IndicatorMappingSurveyType.objects.filter(
                indicator_mapping__indicator=OuterRef("id"),
                survey_type_id=type_,
                is_mandatory=True,
            ).values("is_mandatory")[:1]
            qs = qs.annotate(is_type_mandatory=Subquery(mandatory_type_sub_q))
        else:
            indicator_type_filter = Q()
            qs = qs.annotate(
                is_type_mandatory=Value(False, output_field=BooleanField())
            )
        if mode_:
            indicator_mode_filter = Q(
                mapping__indicatormappingsurveytype__modes__survey_mode=mode_
            )
            mandatory_mode_sub_q = IndicatorMappingSurveyMode.objects.filter(
                survey_type__survey_type=type_,
                survey_type__indicator_mapping__indicator=OuterRef("id"),
                survey_mode_id=mode_,
                is_mandatory=True,
            ).values("is_mandatory")[:1]
            qs = qs.annotate(is_mode_mandatory=Subquery(mandatory_mode_sub_q))
        else:
            indicator_mode_filter = Q()
            qs = qs.annotate(
                is_mode_mandatory=Value(False, output_field=BooleanField())
            )
        # Attributes filtering
        if attributes_ and attributes_.strip():
            # Attributes parameter is provided and not empty
            attributes_list = [
                int(attr_id) for attr_id in attributes_.split(",") if attr_id.strip()
            ]
            mandatory_attributes_sub_q = IndicatorMappingSurveyAttribute.objects.filter(
                indicator_mapping__indicator=OuterRef("id"),
                survey_attribute_id__in=attributes_list,
                is_mandatory=True,
            ).values("is_mandatory")[:1]
            qs = qs.annotate(
                is_attributes_mandatory=Subquery(mandatory_attributes_sub_q)
            )

            # Include indicators with matching attributes or no attributes
            indicator_attributes_filter = Q(
                mapping__survey_attributes__in=attributes_list
            ) | Q(mapping__survey_attributes__isnull=True)
            # Exclude  indicators with attributes not in the list
            indicator_attributes_exclude = Q(
                mapping__survey_attributes__isnull=False
            ) & ~Q(mapping__survey_attributes__in=attributes_list)
        else:
            qs = qs.annotate(
                is_attributes_mandatory=Value(False, output_field=BooleanField())
            )
            # Include indicators with no attributes only
            indicator_attributes_filter = Q(mapping__survey_attributes__isnull=True)
            indicator_attributes_exclude = Q(mapping__survey_attributes__isnull=False)
        # 5) Finally, filter to keep mandatory ones OR ones that match type/mode
        return qs.filter(
            Q(is_type_mandatory=True)
            | Q(is_mode_mandatory=True)
            | Q(is_attributes_mandatory=True)
            | (
                indicator_type_filter
                & indicator_mode_filter
                & indicator_attributes_filter
            ),
            question_count__gt=0,
        ).exclude(indicator_attributes_exclude)
