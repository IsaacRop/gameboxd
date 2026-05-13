import django_filters
from django.db.models import TextField
from django.db.models.functions import Cast

from apps.reviews.models import Review


class ReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter(field_name="rating", lookup_expr="exact")
    rating_min = django_filters.NumberFilter(field_name="rating", lookup_expr="gte")
    rating_max = django_filters.NumberFilter(field_name="rating", lookup_expr="lte")
    contains_spoiler = django_filters.BooleanFilter(field_name="contains_spoiler")
    game = django_filters.UUIDFilter(field_name="game__id")
    user = django_filters.CharFilter(field_name="user__username", lookup_expr="exact")
    genre = django_filters.CharFilter(method="filter_genre")
    platform = django_filters.CharFilter(method="filter_platform")
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Review
        fields = ["rating", "contains_spoiler", "game", "user"]

    def filter_genre(self, queryset, name, value):
        return queryset.annotate(
            _genres_text=Cast("game__genres", output_field=TextField())
        ).filter(_genres_text__icontains=value)

    def filter_platform(self, queryset, name, value):
        return queryset.annotate(
            _platforms_text=Cast("game__platforms", output_field=TextField())
        ).filter(_platforms_text__icontains=value)
