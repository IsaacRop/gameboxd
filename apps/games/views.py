import httpx
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.games.models import Game
from apps.games.serializers import GameSerializer
from apps.games.services import search_and_sync


class GameSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response(
                {"error": "O parâmetro q deve ter no mínimo 2 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            games = search_and_sync(q)
        except httpx.HTTPError:
            return Response(
                {"error": "Serviço IGDB indisponível."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(GameSerializer(games, many=True).data)


class GameListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GameSerializer

    def get_queryset(self):
        qs = Game.objects.all()
        name = self.request.query_params.get("name", "").strip()
        if name:
            qs = qs.filter(title__icontains=name)
        return qs


class GameDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GameSerializer
    queryset = Game.objects.all()
