from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.activity.models import ActivityFeed, List, Log
from apps.games.models import Game

User = get_user_model()


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


class _UserNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")
        read_only_fields = fields


class GameListSerializer(serializers.ModelSerializer):
    user = _UserNestedSerializer(read_only=True)
    games_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = List
        fields = ("id", "user", "title", "description", "is_public", "games_count", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at", "games_count")


class GameListDetailSerializer(GameListSerializer):
    games = serializers.SerializerMethodField()

    class Meta(GameListSerializer.Meta):
        fields = GameListSerializer.Meta.fields + ("games",)

    def get_games(self, obj):
        list_games = obj.games.all()  # ListGame queryset, prefetched with game
        return _GameNestedSerializer([lg.game for lg in list_games], many=True).data


class CreateGameListSerializer(serializers.ModelSerializer):
    class Meta:
        model = List
        fields = ("title", "description", "is_public")
        extra_kwargs = {
            "title": {"max_length": 100},
            "description": {"max_length": 500, "required": False},
            "is_public": {"default": True, "required": False},
        }

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class AddGameToListSerializer(serializers.Serializer):
    game_id = serializers.UUIDField()

    def validate_game_id(self, value):
        if not Game.objects.filter(id=value).exists():
            raise serializers.ValidationError("Jogo não encontrado.")
        return value


class _FeedUserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "avatar")
        read_only_fields = fields

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class ActivityFeedSerializer(serializers.ModelSerializer):
    user = _FeedUserSerializer(read_only=True)
    payload = serializers.SerializerMethodField()

    class Meta:
        model = ActivityFeed
        fields = ("id", "user", "event_type", "payload", "created_at")
        read_only_fields = fields

    def get_payload(self, obj):
        et = obj.event_type
        if et == ActivityFeed.REVIEW_CREATED and obj.review_id:
            return {
                "game_title": obj.review.game.title,
                "game_cover_url": obj.review.game.cover_url,
                "rating": str(obj.review.rating),
                "body_preview": obj.review.body[:120],
                "contains_spoiler": obj.review.contains_spoiler,
            }
        if et == ActivityFeed.LOG_UPDATED and obj.game_log_id:
            return {
                "game_title": obj.game_log.game.title,
                "game_cover_url": obj.game_log.game.cover_url,
                "status": obj.game_log.status,
            }
        if et == ActivityFeed.LIST_CREATED and obj.game_list_id:
            return {
                "list_id": str(obj.game_list.id),
                "list_title": obj.game_list.title,
                "games_count": len(obj.game_list.games.all()),
            }
        if et == ActivityFeed.FOLLOW and obj.followed_user_id:
            return {
                "followed_username": obj.followed_user.username,
                "followed_avatar": obj.followed_user.avatar.url if obj.followed_user.avatar else None,
            }
        return {}
