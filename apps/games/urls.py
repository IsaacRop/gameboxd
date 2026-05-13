from django.urls import path

from apps.games.views import GameDetailView, GameListView, GameSearchView

urlpatterns = [
    path("", GameListView.as_view(), name="game-list"),
    path("search/", GameSearchView.as_view(), name="game-search"),
    path("<uuid:pk>/", GameDetailView.as_view(), name="game-detail"),
]
