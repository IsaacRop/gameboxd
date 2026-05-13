from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activity.filters import GameLogFilter
from apps.activity.models import ActivityFeed, List, ListGame, Log
from apps.activity.serializers import (
    ActivityFeedSerializer,
    AddGameToListSerializer,
    CreateGameListSerializer,
    CreateGameLogSerializer,
    GameListDetailSerializer,
    GameListSerializer,
    GameLogSerializer,
    UpdateGameLogSerializer,
)
from apps.games.models import Game
from apps.users.models import Follow, User


def _log_qs(user):
    return (
        Log.objects
        .filter(user=user)
        .select_related("game")
        .order_by("-updated_at")
    )


class GameLogListCreateView(generics.ListCreateAPIView):
    """
    Lista logs com suporte a filtros:
    - ?status=completed|playing|dropped|want_to_play
    - ?game={uuid} — UUID do jogo
    - ?genre=RPG — gênero do jogo (parcial, case-insensitive)
    - ?platform=PlayStation — plataforma (parcial, case-insensitive)
    - ?updated_after=2026-01-01
    - ?updated_before=2026-12-31
    - ?search=texto — busca no título do jogo
    - ?ordering=updated_at,game__title,status (- para decrescente)
    """
    permission_classes = [IsAuthenticated]
    filterset_class = GameLogFilter
    search_fields = ["game__title"]
    ordering_fields = ["updated_at", "game__title", "status"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        return CreateGameLogSerializer if self.request.method == "POST" else GameLogSerializer

    def get_queryset(self):
        return _log_qs(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = CreateGameLogSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        log = serializer.save()
        log = _log_qs(request.user).get(pk=log.pk)
        return Response(GameLogSerializer(log).data, status=status.HTTP_201_CREATED)


class GameLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UpdateGameLogSerializer
        return GameLogSerializer

    def get_queryset(self):
        return _log_qs(self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = UpdateGameLogSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        log = serializer.save()
        log = _log_qs(request.user).get(pk=log.pk)
        return Response(GameLogSerializer(log).data)

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _list_qs():
    return (
        List.objects
        .select_related("user")
        .annotate(games_count=Count("games"))
        .order_by("-updated_at")
    )


def _list_detail_qs():
    return (
        List.objects
        .select_related("user")
        .prefetch_related("games__game")
        .annotate(games_count=Count("games"))
        .order_by("-updated_at")
    )


class GameListListCreateView(generics.ListCreateAPIView):
    """
    Lista game lists com suporte a filtros:
    - ?user=username — listas públicas de outro usuário
    - ?search=texto — busca em título e descrição
    - ?ordering=title,created_at,updated_at (- para decrescente)
    """
    permission_classes = [IsAuthenticated]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "created_at", "updated_at"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        return CreateGameListSerializer if self.request.method == "POST" else GameListSerializer

    def get_queryset(self):
        username = self.request.query_params.get("user")
        if username:
            return _list_qs().filter(user__username=username, is_public=True)
        return _list_qs().filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = CreateGameListSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        game_list = serializer.save()
        game_list = _list_qs().get(pk=game_list.pk)
        return Response(GameListSerializer(game_list).data, status=status.HTTP_201_CREATED)


class GameListDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CreateGameListSerializer
        return GameListDetailSerializer

    def get_queryset(self):
        # Owner sees own lists (private+public); others see only public
        return _list_detail_qs().filter(
            Q(user=self.request.user) | Q(is_public=True)
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"error": "Você não tem permissão para editar esta lista."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CreateGameListSerializer(instance, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        game_list = serializer.save()
        game_list = _list_detail_qs().get(pk=game_list.pk)
        return Response(GameListDetailSerializer(game_list).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"error": "Você não tem permissão para deletar esta lista."}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GameListAddRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_owned_list(self, pk, user):
        game_list = get_object_or_404(List, pk=pk)
        if game_list.user != user:
            return None, Response({"error": "Você não tem permissão para modificar esta lista."}, status=status.HTTP_403_FORBIDDEN)
        return game_list, None

    def post(self, request, pk):
        game_list, err = self._get_owned_list(pk, request.user)
        if err:
            return err
        serializer = AddGameToListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game = Game.objects.get(id=serializer.validated_data["game_id"])
        if ListGame.objects.filter(list=game_list, game=game).exists():
            return Response({"error": "Jogo já está nesta lista."}, status=status.HTTP_400_BAD_REQUEST)
        ListGame.objects.create(list=game_list, game=game)
        games_count = game_list.games.count()
        return Response({"message": "Jogo adicionado.", "games_count": games_count}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, game_id):
        game_list, err = self._get_owned_list(pk, request.user)
        if err:
            return err
        deleted, _ = ListGame.objects.filter(list=game_list, game_id=game_id).delete()
        if not deleted:
            return Response({"error": "Jogo não encontrado nesta lista."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _feed_qs(filters):
    return (
        ActivityFeed.objects
        .filter(**filters)
        .select_related(
            "user",
            "review__game",
            "game_log__game",
            "game_list",
            "followed_user",
        )
        .prefetch_related("game_list__games")
        .order_by("-created_at")
    )


class FeedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityFeedSerializer

    def get_queryset(self):
        following_ids = Follow.objects.filter(
            follower=self.request.user
        ).values_list("following_id", flat=True)
        return _feed_qs({"user__in": following_ids})

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            if not qs.exists():
                response.data["message"] = "Siga outros jogadores para ver o feed."
            return response
        serializer = self.get_serializer(qs, many=True)
        data = serializer.data
        if not data:
            return Response({"message": "Siga outros jogadores para ver o feed.", "results": []})
        return Response(data)


class UserActivityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityFeedSerializer

    def get_queryset(self):
        username = self.kwargs["username"]
        user = get_object_or_404(User, username=username)
        return _feed_qs({"user": user}).exclude(
            Q(event_type=ActivityFeed.LIST_CREATED) & Q(game_list__is_public=False)
        )
