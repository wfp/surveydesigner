import io
import os
import uuid
from json import JSONDecodeError
from xml.etree import ElementTree as ET

import django_rq
import requests
from accounts.models import UserAPISiteAPITypes
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.files.base import ContentFile
from django.db.models import BooleanField, Count, OuterRef, Prefetch, Q, Subquery, Value
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
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
from questions.models import BaseQuestion, RepeatSection, RootQuestion, SubQuestion
from questions.services import DocConversion, XLSForm, XMLConversion
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rq.exceptions import NoSuchJobError
from rq.job import Job
from surveys.models import Survey


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


def get_xlsx_from_request(get_serializer, request, as_wb=False):
    serializer = get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return get_xlsx_from_data(data, as_wb=as_wb)


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

    def _handle_bad_response(self, response):
        try:
            details = response.json()
        except JSONDecodeError:
            details = {}

        raise ValidationError(
            detail={
                "message": "Error Occurred",
                "details": details,
                "code": response.status_code,
            }
        )

    def handle_kobo(self, url, xlsx_form, xlsx_file, token):
        name = xlsx_form.id_name

        response = requests.post(
            f"{url}?format=json",
            data={"asset_type": "empty", "name": name, "settings": {}},
            headers={"Authorization": f"Token {token}"},
        )

        if not response.ok:
            self._handle_bad_response(response)

        data = response.json()
        uid = data["uid"]

        upload_response = requests.post(
            "https://kobo.humanitarianresponse.info/api/v2/imports/",
            data={"assetUid": uid, "destination": data["url"], "name": name},
            files={"file": (f"{name}.xlsx", xlsx_file)},
            headers={"Authorization": f"Token {token}"},
        )

        if not upload_response.ok:
            self._handle_bad_response(upload_response)

        preview_url = f"https://kobo.humanitarianresponse.info/#/forms/{uid}/landing"

        return Response({"preview_url": preview_url})

    def handle_ona(self, site, url, xlsx_form, xlsx_file, token):
        response = requests.post(
            url,
            files={"xls_file": (f"{xlsx_form.id_name}.xlsx", xlsx_file)},
            headers={"Authorization": f"Token {token}"},
        )

        if not response.ok:
            self._handle_bad_response(response)

        data = response.json()

        response_payload = {
            "preview_url": data.get("enketo_preview_url", ""),
        }

        external_files = getattr(xlsx_form, "external_files", {})
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

        for file_name, field_file in external_files.items():
            if not field_file:
                continue

            try:
                field_file.open("rb")
            except FileNotFoundError:
                raise ValidationError(
                    {"message": f"Choices file '{file_name}' could not be found."}
                )
            except Exception as exc:
                raise ValidationError(
                    {
                        "message": f"Unable to open choices file '{file_name}' for Moda metadata upload: {exc}"
                    }
                )

            try:
                file_obj = getattr(field_file, "file", field_file)
                files = {
                    "xform": (None, str(form_id)),
                    "data_type": (None, "media"),
                    "data_value": (None, file_name),
                    "data_file": (file_name, file_obj, "text/csv"),
                }
                response = requests.post(
                    metadata_url,
                    headers=headers,
                    files=files,
                )
            finally:
                field_file.close()

            if not response.ok:
                self._handle_moda_metadata_error(response, file_name)

            uploaded_files.append(file_name)

        return uploaded_files

    def _handle_moda_metadata_error(self, response, file_name):
        try:
            details = response.json()
        except JSONDecodeError:
            details = {}

        raise ValidationError(
            detail={
                "message": f"Failed to upload metadata file '{file_name}' to Moda.",
                "details": details,
                "code": response.status_code,
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        xlsx_form = get_xlsx_from_data(data, as_wb=True)
        xlsx_file = xlsx_form.generate()

        api_key_id = data.get("id")
        project_id = data.get("project_id")

        api_configuration = self.request.user.api_keys.filter(id=api_key_id).first()
        site = api_configuration.site

        if site.is_ona and not project_id:
            return Response(
                {"message": "Project is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        url = UserAPISiteAPITypes.get_upload_url(site, project_id)

        if not (url or api_configuration):
            return Response(
                {"message": "Configuration for that site not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = api_configuration.get_key()

        if site.is_kobo:
            return self.handle_kobo(url, xlsx_form, xlsx_file, token)
        if site.is_ona:
            return self.handle_ona(site, url, xlsx_form, xlsx_file, token)

        return ValidationError({"message": "Site is not configured."})


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
        xlsx = get_xlsx_from_request(self.get_serializer, request)
        response = HttpResponse(
            xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=survey.xlsx"
        return response


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
        xlsx_form = get_xlsx_from_request(self.get_serializer, request, as_wb=True)
        xlsx_b = io.BytesIO(xlsx_form.generate())
        xml_conversion = XMLConversion(xlsx_b)
        xml_data = xml_conversion.run()

        url = ""
        enketo_url = ""
        external_files = getattr(xlsx_form, "external_files", {})
        if xml_data:
            preview_id = uuid.uuid4().hex
            storage_prefix = os.path.join("previews", preview_id)
            survey = Survey.objects.create()
            storage = survey.file.storage

            file_url_map = {}
            for filename, file_obj in external_files.items():
                if not filename or not file_obj:
                    continue
                try:
                    data = self._read_file_content(file_obj)
                except FileNotFoundError:
                    continue
                if data is None:
                    continue

                storage_path = storage.save(
                    f"{storage_prefix}/{filename}", ContentFile(data)
                )
                file_url_map[filename] = storage.url(storage_path)

            xml_input = (
                xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data
            )
            try:
                root = ET.fromstring(xml_input)
            except (ET.ParseError, ValueError):
                root = None

            if root is not None and file_url_map:
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

        response = {
            "url": url,
            "enketo_url": enketo_url,
            "warnings": xml_conversion.warnings,
            "errors": xml_conversion.errors,
        }
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

    @method_decorator(vary_on_cookie)
    @method_decorator(cache_page(60 * 60, key_prefix="modules_"))  # Cache for 1 hour
    def dispatch(self, *args, **kwargs):
        return super(ModelViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()

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

    @method_decorator(vary_on_cookie)
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        submodule_ids = self.request.query_params.get("submodule_ids")
        indicator_ids = self.request.query_params.get("indicator_ids")
        submodule_ids_set = set()
        if submodule_ids:
            submodule_ids_set.update(set(submodule_ids.split(",")))
        # get submodules related to indicators through BaseQuestion
        if indicator_ids:
            indicator_ids = indicator_ids.split(",")
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
        qs = (
            super()
            .get_queryset()
            .annotate(
                sub_question_count=Count(
                    "root_questions__sub_questions",
                    distinct=True,
                ),
            )
        )

        sub_questions_prefetch = Prefetch(
            "sub_questions",
            queryset=SubQuestion.objects.all()
            .order_by()
            .select_related("suffix", "suffix_2", "recall_period")
            .prefetch_related("translations"),
        )

        # Filter root_questions by indicator for use in SubmoduleWithQuestionsSerializer
        query = Q(submodule__in=qs)
        indicator_ids = self.request.query_params.get("indicator_ids")
        if indicator_ids:
            indicator_ids = indicator_ids.split(",")
            base_questions = BaseQuestion.objects.filter(
                indicators__in=indicator_ids
            ).values_list("id", flat=True)
            query |= Q(base_question__in=base_questions)

        root_questions_prefetch = Prefetch(
            "root_questions",
            queryset=RootQuestion.objects.filter(query)
            .prefetch_related(
                "translations",
                sub_questions_prefetch,
            )
            .order_by(),
            to_attr="filtered_root_questions",
        )

        repeat_section_prefetch = Prefetch(
            "repeat_sections",
            queryset=RepeatSection.objects.prefetch_related("translations"),
        )

        return qs.prefetch_related(
            root_questions_prefetch, repeat_section_prefetch
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

    @method_decorator(vary_on_cookie)
    @method_decorator(cache_page(60 * 60))
    def get(self, request, *args, **kwargs):
        submodule_ids = (
            self.request.query_params.get("submodule_ids", "").replace(",", " ").split()
        )
        indicator_ids = (
            self.request.query_params.get("indicator_ids", "").replace(",", " ").split()
        )
        all_submodule_ids = (
            self.request.query_params.get("all_submodule_ids", "")
            .replace(",", " ")
            .split()
        )
        result = []

        if submodule_ids:
            submodule_ids = [int(id_) for id_ in submodule_ids]
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

    @method_decorator(vary_on_cookie)
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        # 1) Build a “base” QuerySet with common annotations/prefetch
        qs = (
            super()
            .get_queryset()
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
