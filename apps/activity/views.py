from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activity.models import List, ListGame, Log
from apps.activity.serializers import (
    AddGameToListSerializer,
    CreateGameListSerializer,
    CreateGameLogSerializer,
    GameListDetailSerializer,
    GameListSerializer,
    GameLogSerializer,
    UpdateGameLogSerializer,
)
from apps.games.models import Game


def _log_qs(user):
    return (
        Log.objects
        .filter(user=user)
        .select_related("game")
        .order_by("-updated_at")
    )


class GameLogListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return CreateGameLogSerializer if self.request.method == "POST" else GameLogSerializer

    def get_queryset(self):
        qs = _log_qs(self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        game_id = self.request.query_params.get("game")
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs

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
    permission_classes = [IsAuthenticated]

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
