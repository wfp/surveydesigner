from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from modules.models import Module, Submodule, SubmoduleMapping


def invalidate_module_cache():
    cache.delete_pattern("*modules_*")


@receiver(post_save, sender=SubmoduleMapping)
@receiver(post_delete, sender=SubmoduleMapping)
def handle_submodule_mapping_change(sender, instance, **kwargs):
    invalidate_module_cache()


@receiver(post_save, sender=Module)
@receiver(post_delete, sender=Module)
@receiver(post_save, sender=Submodule)
@receiver(post_delete, sender=Submodule)
def handle_module_metadata_change(sender, instance, **kwargs):
    invalidate_module_cache()


@receiver(m2m_changed, sender=SubmoduleMapping.survey_categories.through)
@receiver(m2m_changed, sender=SubmoduleMapping.survey_types.through)
@receiver(m2m_changed, sender=SubmoduleMapping.survey_attributes.through)
def handle_m2m_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        invalidate_module_cache()
