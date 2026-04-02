from django.contrib.admin.options import LOOKUP_SEP
from django.contrib.admin.utils import lookup_spawns_duplicates
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.functions import Cast, Collate
from django.forms import Textarea
from django.utils.text import smart_split, unescape_string_literal


class FormFieldOverridesMixin:
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 2, "cols": 70})},
    }


class AdminUserTrackingMixin:
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if hasattr(obj, "created_by") and not obj.created_by_id:
            obj.created_by = request.user

        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user
        obj.save()

    def modified_by(self, obj):
        return obj.updated_by

    modified_by.short_description = "Modified By"

    def modified_on(self, obj):
        return obj.date_updated

    modified_on.short_description = "Modified On"
    modified_on.admin_order_field = "date_updated"


class CollationSafeSearchAdminMixin:
    search_collation = "C"

    def get_search_results(self, request, queryset, search_term):
        """
        Django admin's default search uses LIKE-based lookups for text fields.
        PostgreSQL 16 rejects LIKE against our nondeterministic ICU collation,
        so collated fields are searched through a deterministic alias instead.
        """

        def resolve_field(field_name):
            opts = queryset.model._meta
            prev_field = None
            lookup_fields = field_name.split(LOOKUP_SEP)

            for path_part in lookup_fields:
                if path_part == "pk":
                    path_part = opts.pk.name
                try:
                    field = opts.get_field(path_part)
                except FieldDoesNotExist:
                    return prev_field

                prev_field = field
                if hasattr(field, "path_infos"):
                    opts = field.path_infos[-1].to_opts

            return prev_field

        def build_lookup(field_name, lookup, alias_index):
            field = resolve_field(field_name)
            if isinstance(field, (models.CharField, models.TextField)) and getattr(
                field, "db_collation", None
            ):
                alias_name = f"_collation_safe_search_{alias_index}"
                alias = Collate(field_name, self.search_collation)
                return f"{alias_name}__{lookup}", {alias_name: alias}
            return f"{field_name}__{lookup}", None

        def construct_search(field_name, alias_index):
            if field_name.startswith("^"):
                return build_lookup(
                    field_name.removeprefix("^"), "istartswith", alias_index
                )
            if field_name.startswith("="):
                return build_lookup(field_name.removeprefix("="), "iexact", alias_index)
            if field_name.startswith("@"):
                return f"{field_name.removeprefix('@')}__search", None

            opts = queryset.model._meta
            lookup_fields = field_name.split(LOOKUP_SEP)
            prev_field = None
            for i, path_part in enumerate(lookup_fields):
                if path_part == "pk":
                    path_part = opts.pk.name
                try:
                    field = opts.get_field(path_part)
                except FieldDoesNotExist:
                    if prev_field and prev_field.get_lookup(path_part):
                        if path_part == "exact" and not isinstance(
                            prev_field, (models.CharField, models.TextField)
                        ):
                            field_name_without_exact = "__".join(lookup_fields[:i])
                            alias_name = f"_collation_safe_cast_{alias_index}"
                            alias = Cast(
                                field_name_without_exact,
                                output_field=models.CharField(),
                            )
                            return f"{alias_name}__exact", {alias_name: alias}
                        return field_name, None
                else:
                    prev_field = field
                    if hasattr(field, "path_infos"):
                        opts = field.path_infos[-1].to_opts

            return build_lookup(field_name, "icontains", alias_index)

        may_have_duplicates = False
        search_fields = self.get_search_fields(request)
        if search_fields and search_term:
            aliases = {}
            orm_lookups = []
            for index, field in enumerate(search_fields):
                lookup, alias = construct_search(str(field), index)
                orm_lookups.append(lookup)
                if alias:
                    aliases.update(alias)

            if aliases:
                queryset = queryset.alias(**aliases)

            term_queries = []
            for bit in smart_split(search_term):
                if bit.startswith(('"', "'")) and bit[0] == bit[-1]:
                    bit = unescape_string_literal(bit)
                or_queries = models.Q.create(
                    [(orm_lookup, bit) for orm_lookup in orm_lookups],
                    connector=models.Q.OR,
                )
                term_queries.append(or_queries)

            queryset = queryset.filter(models.Q.create(term_queries))
            may_have_duplicates |= any(
                lookup_spawns_duplicates(self.opts, search_spec)
                for search_spec in orm_lookups
            )

        return queryset, may_have_duplicates
