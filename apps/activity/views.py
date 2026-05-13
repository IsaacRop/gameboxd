from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.activity.models import Log
from apps.activity.serializers import (
    CreateGameLogSerializer,
    GameLogSerializer,
    UpdateGameLogSerializer,
)


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
