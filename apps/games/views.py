import httpx
from django.db.models import TextField
from django.db.models.functions import Cast
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.pagination import GameCursorPagination
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
    """
    Lista jogos com suporte a filtros:
    - ?name=texto — título (parcial, case-insensitive)
    - ?genre=RPG — gênero (parcial, case-insensitive)
    - ?platform=PlayStation — plataforma (parcial, case-insensitive)
    - ?rating_min=3.0 — rating mínimo
    - ?search=texto — busca em título e sumário
    - ?ordering=title,rating,release_year (- para decrescente)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = GameCursorPagination
    serializer_class = GameSerializer
    search_fields = ["title", "summary"]
    ordering_fields = ["title", "rating", "release_year"]
    ordering = ["title"]

    def get_queryset(self):
        qs = Game.objects.all()
        params = self.request.query_params

        name = params.get("name", "").strip()
        if name:
            qs = qs.filter(title__icontains=name)

        genre = params.get("genre", "").strip()
        if genre:
            qs = qs.annotate(
                _genres_text=Cast("genres", output_field=TextField())
            ).filter(_genres_text__icontains=genre)

        platform = params.get("platform", "").strip()
        if platform:
            qs = qs.annotate(
                _platforms_text=Cast("platforms", output_field=TextField())
            ).filter(_platforms_text__icontains=platform)

        rating_min = params.get("rating_min", "").strip()
        if rating_min:
            try:
                qs = qs.filter(rating__gte=float(rating_min))
            except ValueError:
                pass

        return qs


class GameDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GameSerializer
    queryset = Game.objects.all()
