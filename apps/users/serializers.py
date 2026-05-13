from django.contrib.auth import authenticate
from django.db.models import Count
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Follow, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "As senhas não coincidem."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "bio", "avatar", "created_at")
        read_only_fields = ("id", "created_at")


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("bio", "avatar")


class PublicUserSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    saves_count = serializers.IntegerField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "bio", "avatar", "created_at",
            "followers_count", "following_count", "saves_count",
            "reviews_count", "is_following",
        )
        read_only_fields = fields

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        following_ids = self.context.get("following_ids")
        if following_ids is not None:
            return obj.pk in following_ids
        return Follow.objects.filter(follower=request.user, following=obj).exists()


class StatsSerializer(serializers.Serializer):
    saves_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    playing_count = serializers.IntegerField()
    dropped_count = serializers.IntegerField()
    want_to_play_count = serializers.IntegerField()
    reviews_count = serializers.IntegerField()
    followers_count = serializers.IntegerField()
    following_count = serializers.IntegerField()


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.StringRelatedField()
    following = serializers.StringRelatedField()

    class Meta:
        model = Follow
        fields = ("id", "follower", "following", "created_at")
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError({"error": "E-mail ou senha inválidos."})
        if not user.is_active:
            raise serializers.ValidationError({"error": "Conta desativada."})
        attrs["user"] = user
        return attrs


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def annotated_users_qs():
    return User.objects.annotate(
        followers_count=Count("followers_set", distinct=True),
        following_count=Count("following_set", distinct=True),
        saves_count=Count("logs", distinct=True),
        reviews_count=Count("reviews", distinct=True),
    )
