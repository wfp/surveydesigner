from django.urls import path
from rest_framework import routers

from .views import (
    GenerateDocForm,
    GenerateXLSForm,
    IndicatorViewSet,
    ModuleViewSet,
    PreviewXLSForm,
    SubmodulesOrderValidationView,
    SubmoduleViewSet,
    UploadXLSForm,
    ValidateXLSForm,
)

router = routers.SimpleRouter()
router.register(r"modules", ModuleViewSet)
router.register(r"submodules", SubmoduleViewSet)
router.register(r"indicators", IndicatorViewSet)
urlpatterns = router.urls


urlpatterns.extend(
    [
        path("generate/", GenerateXLSForm.as_view(), name="generate_xls_form"),
        path("generate-doc/", GenerateDocForm.as_view(), name="generate_doc_form"),
        path("upload/", UploadXLSForm.as_view(), name="upload_xls_form"),
        path("preview/", PreviewXLSForm.as_view(), name="preview_xls_form"),
        path("validate/", ValidateXLSForm.as_view(), name="validate_xls_form"),
        path(
            "order-validation/",
            SubmodulesOrderValidationView.as_view(),
            name="submodule_order_validation",
        ),
    ]
)
