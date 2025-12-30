from typing import Type

from django.db import models
from django.urls import reverse


def get_model_admin_base_url(
    model: Type[models.Model], suffix: str, args=None, kwargs=None
):
    return reverse(
        f"admin:{model._meta.app_label}_{model._meta.model_name}{suffix}",
        args=args,
        kwargs=kwargs,
    )
