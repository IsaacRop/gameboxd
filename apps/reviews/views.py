from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return CreateReviewSerializer if self.request.method == "POST" else ReviewSerializer

    def get_queryset(self):
        qs = _review_qs()
        params = self.request.query_params

        game_id = params.get("game")
        if game_id:
            qs = qs.filter(game_id=game_id)

        username = params.get("user")
        if username:
            qs = qs.filter(user__username=username)

        rating = params.get("rating")
        if rating:
            qs = qs.filter(rating=rating)

        return qs

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
