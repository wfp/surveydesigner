from django.db.models import Q, QuerySet
from django.db.models.functions import Coalesce


class BaseQuestionQuerySet(QuerySet):
    def filter_by_names(self, names):
        return self.filter(
            Q(root_question__name__in=names) | Q(sub_question__name__in=names)
        )

    def annotate_type(self):
        return self.annotate(
            annotated_type=Coalesce(
                "root_question__type",
                "sub_question__suffix_2__type",
                "sub_question__suffix__type",
                "sub_question__root_question__type",
            )
        )

    def filter_by_types(self, types, annotate_type=False):
        queryset = self
        if annotate_type:
            queryset = queryset.annotate_type()
        return queryset.filter(annotated_type__in=types)
