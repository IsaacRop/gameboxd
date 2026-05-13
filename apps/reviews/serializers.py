from rest_framework import serializers

from apps.games.models import Game
from apps.reviews.models import Like, Review


class _UserMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()


class _GameMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()


class ReviewSerializer(serializers.ModelSerializer):
    user = _UserMinimalSerializer(read_only=True)
    game = _GameMinimalSerializer(read_only=True)
    rating = serializers.IntegerField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id", "user", "game", "rating", "body",
            "contains_spoiler", "likes_count", "liked_by_me",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at", "likes_count", "liked_by_me")

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # usa o prefetch_related('likes') feito na view — sem query extra
        return any(like.user_id == request.user.pk for like in obj.likes.all())


class CreateReviewSerializer(serializers.ModelSerializer):
    game = serializers.PrimaryKeyRelatedField(queryset=Game.objects.all())
    rating = serializers.IntegerField(min_value=1, max_value=5)
    body = serializers.CharField(max_length=2000, allow_blank=True, default="")

    class Meta:
        model = Review
        fields = ("game", "rating", "body", "contains_spoiler")

    def validate(self, attrs):
        user = self.context["request"].user
        if Review.objects.filter(user=user, game=attrs["game"]).exists():
            raise serializers.ValidationError(
                {"error": "Você já tem uma review para esse jogo."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class UpdateReviewSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    body = serializers.CharField(max_length=2000, allow_blank=True, required=False)

    class Meta:
        model = Review
        fields = ("rating", "body", "contains_spoiler")
