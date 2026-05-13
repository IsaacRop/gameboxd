import django_filters
from django.db.models import TextField
from django.db.models.functions import Cast

from apps.activity.models import Log


class GameLogFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status", lookup_expr="exact")
    game = django_filters.UUIDFilter(field_name="game__id")
    genre = django_filters.CharFilter(method="filter_genre")
    platform = django_filters.CharFilter(method="filter_platform")
    updated_after = django_filters.DateFilter(field_name="updated_at", lookup_expr="date__gte")
    updated_before = django_filters.DateFilter(field_name="updated_at", lookup_expr="date__lte")

    class Meta:
        model = Log
        fields = ["status", "game"]

    def filter_genre(self, queryset, name, value):
        return queryset.annotate(
            _genres_text=Cast("game__genres", output_field=TextField())
        ).filter(_genres_text__icontains=value)

    def filter_platform(self, queryset, name, value):
        return queryset.annotate(
            _platforms_text=Cast("game__platforms", output_field=TextField())
        ).filter(_platforms_text__icontains=value)
