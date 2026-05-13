from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.pagination import StandardCursorPagination
from apps.reviews.filters import ReviewFilter
from apps.reviews.models import Like, Review
from apps.reviews.permissions import IsOwnerOrReadOnly
from apps.reviews.serializers import (
    CreateReviewSerializer,
    ReviewSerializer,
    UpdateReviewSerializer,
)


def _review_qs():
    return (
        Review.objects
        .select_related("user", "game")
        .prefetch_related("likes")
        .annotate(likes_count=Count("likes", distinct=True))
        .order_by("-created_at")
    )


class ReviewListCreateView(generics.ListCreateAPIView):
    """
    Lista reviews com suporte a filtros:
    - ?rating=5 — nota exata
    - ?rating_min=3 — nota mínima
    - ?rating_max=4 — nota máxima
    - ?contains_spoiler=false
    - ?genre=RPG — gênero do jogo (parcial, case-insensitive)
    - ?platform=PlayStation — plataforma do jogo (parcial, case-insensitive)
    - ?game={uuid} — UUID do jogo
    - ?user=username — reviews de um usuário
    - ?created_after=2026-01-01 — criadas depois desta data
    - ?created_before=2026-12-31
    - ?search=texto — busca em título do jogo e corpo da review
    - ?ordering=rating,-created_at — ordenação (- para decrescente)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination
    filterset_class = ReviewFilter
    search_fields = ["game__title", "body"]
    ordering_fields = ["rating", "created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return CreateReviewSerializer if self.request.method == "POST" else ReviewSerializer

    def get_queryset(self):
        return _review_qs()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def create(self, request, *args, **kwargs):
        serializer = CreateReviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        # re-fetch com anotações para retornar likes_count e liked_by_me
        review = _review_qs().get(pk=review.pk)
        return Response(
            ReviewSerializer(review, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UpdateReviewSerializer
        return ReviewSerializer

    def get_queryset(self):
        return _review_qs()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = UpdateReviewSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        review = _review_qs().get(pk=review.pk)
        return Response(ReviewSerializer(review, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikeView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_review(self, pk):
        return get_object_or_404(Review, pk=pk)

    def post(self, request, pk):
        review = self._get_review(pk)

        if review.user == request.user:
            return Response(
                {"error": "Você não pode curtir a própria review."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, created = Like.objects.get_or_create(user=request.user, review=review)
        if not created:
            return Response(
                {"error": "Você já curtiu essa review."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        likes_count = Like.objects.filter(review=review).count()
        return Response(
            {"message": "Review curtida.", "likes_count": likes_count},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, pk):
        review = self._get_review(pk)
        deleted, _ = Like.objects.filter(user=request.user, review=review).delete()
        if not deleted:
            return Response(
                {"error": "Você não curtiu essa review."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
