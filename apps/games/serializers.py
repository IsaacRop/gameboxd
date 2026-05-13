from rest_framework import serializers

from apps.games.models import Game


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = (
            "id", "igdb_id", "title", "slug", "cover_url",
            "summary", "genres", "platforms", "release_year", "rating",
        )
        read_only_fields = fields
