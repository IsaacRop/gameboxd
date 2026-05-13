from django.urls import path

from apps.activity.views import GameLogDetailView, GameLogListCreateView

urlpatterns = [
    path("", GameLogListCreateView.as_view(), name="log-list"),
    path("<uuid:pk>/", GameLogDetailView.as_view(), name="log-detail"),
]
