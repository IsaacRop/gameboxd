from django.urls import path

from apps.reviews.views import LikeView, ReviewDetailView, ReviewListCreateView

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="review-list"),
    path("<uuid:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path("<uuid:pk>/like/", LikeView.as_view(), name="review-like"),
]
