from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from config.pagination import StandardCursorPagination

from apps.users.models import Follow, User
from apps.users.serializers import (
    LoginSerializer,
    PublicUserSerializer,
    RegisterSerializer,
    StatsSerializer,
    UserSerializer,
    UserUpdateSerializer,
    annotated_users_qs,
    get_tokens_for_user,
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {**UserSerializer(user).data, **get_tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(
            {**UserSerializer(user).data, **get_tokens_for_user(user)},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "O campo refresh_token é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"error": "Token inválido ou já expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Me ────────────────────────────────────────────────────────────────────────

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = User.objects.filter(pk=request.user.pk).aggregate(
            saves_count=Count("logs", distinct=True),
            completed_count=Count("logs", filter=Q(logs__status="completed"), distinct=True),
            playing_count=Count("logs", filter=Q(logs__status="playing"), distinct=True),
            dropped_count=Count("logs", filter=Q(logs__status="dropped"), distinct=True),
            want_to_play_count=Count("logs", filter=Q(logs__status="want_to_play"), distinct=True),
            reviews_count=Count("reviews", distinct=True),
            followers_count=Count("followers_set", distinct=True),
            following_count=Count("following_set", distinct=True),
        )
        return Response(StatsSerializer(stats).data)


# ── Perfil público ────────────────────────────────────────────────────────────

class PublicProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = PublicUserSerializer
    lookup_field = "username"

    def get_queryset(self):
        return annotated_users_qs()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        ctx["following_ids"] = _following_ids_for(self.request.user)
        return ctx


# ── Follow / Unfollow ─────────────────────────────────────────────────────────

class FollowView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_target(self, username):
        return get_object_or_404(User, username=username)

    def post(self, request, username):
        target = self._get_target(username)

        if target == request.user:
            return Response(
                {"error": "Você não pode seguir a si mesmo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, created = Follow.objects.get_or_create(
            follower=request.user,
            following=target,
        )
        if not created:
            return Response(
                {"error": f"Você já está seguindo {username}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": f"Agora você está seguindo {username}."},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, username):
        target = self._get_target(username)
        deleted, _ = Follow.objects.filter(
            follower=request.user,
            following=target,
        ).delete()
        if not deleted:
            return Response(
                {"error": f"Você não está seguindo {username}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Followers / Following lists ───────────────────────────────────────────────

def _following_ids_for(user):
    if not user or not user.is_authenticated:
        return None
    return set(Follow.objects.filter(follower=user).values_list("following_id", flat=True))


class FollowersListView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardCursorPagination
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        target = get_object_or_404(User, username=self.kwargs["username"])
        follower_ids = Follow.objects.filter(following=target).values_list("follower_id", flat=True)
        return annotated_users_qs().filter(pk__in=follower_ids)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        ctx["following_ids"] = _following_ids_for(self.request.user)
        return ctx


class FollowingListView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardCursorPagination
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        target = get_object_or_404(User, username=self.kwargs["username"])
        following_ids = Follow.objects.filter(follower=target).values_list("following_id", flat=True)
        return annotated_users_qs().filter(pk__in=following_ids)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        ctx["following_ids"] = _following_ids_for(self.request.user)
        return ctx
