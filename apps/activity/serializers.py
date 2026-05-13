from rest_framework import serializers

from apps.activity.models import Log
from apps.games.models import Game


class _GameNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ("id", "title", "cover_url", "rating")
        read_only_fields = fields


class GameLogSerializer(serializers.ModelSerializer):
    game = _GameNestedSerializer(read_only=True)

    class Meta:
        model = Log
        fields = ("id", "game", "status", "played_date", "updated_at")
        read_only_fields = ("id", "updated_at")


class CreateGameLogSerializer(serializers.ModelSerializer):
    game = serializers.PrimaryKeyRelatedField(queryset=Game.objects.all())

    class Meta:
        model = Log
        fields = ("game", "status", "played_date")

    def validate(self, attrs):
        user = self.context["request"].user
        if Log.objects.filter(user=user, game=attrs["game"]).exists():
            raise serializers.ValidationError({
                "error": (
                    "Você já tem esse jogo na sua biblioteca. "
                    "Use PATCH /api/logs/{id}/ para atualizar o status."
                )
            })
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class UpdateGameLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ("status", "played_date")
