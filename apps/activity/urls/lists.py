from django.urls import path

from apps.activity.views import GameListAddRemoveView, GameListDetailView, GameListListCreateView

urlpatterns = [
    path("", GameListListCreateView.as_view(), name="list-list"),
    path("<uuid:pk>/", GameListDetailView.as_view(), name="list-detail"),
    path("<uuid:pk>/games/", GameListAddRemoveView.as_view(), name="list-games"),
    path("<uuid:pk>/games/<uuid:game_id>/", GameListAddRemoveView.as_view(), name="list-games-remove"),
]
