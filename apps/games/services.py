from django.db import IntegrityError

from apps.games.igdb import IGDBClient
from apps.games.models import Game


def search_and_sync(query: str) -> list[Game]:
    client = IGDBClient()
    results = client.search(query)
    games = []
    for data in results:
        igdb_id = data.pop("igdb_id")
        try:
            game, _ = Game.objects.update_or_create(igdb_id=igdb_id, defaults=data)
            games.append(game)
        except IntegrityError:
            # Slug collision — busca o registro existente sem atualizar
            game = Game.objects.filter(igdb_id=igdb_id).first()
            if game:
                games.append(game)
    return games
