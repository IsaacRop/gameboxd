"""
Testes de N+1: cada teste cria N itens, executa o endpoint, cria N*2 itens
e verifica que o número de queries NÃO cresce — prova ausência de N+1.
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.activity.models import ActivityFeed
from apps.users.models import Follow
from tests.factories import (
    FollowFactory,
    GameFactory,
    GameListFactory,
    LogFactory,
    ReviewFactory,
    UserFactory,
)

REVIEWS_URL = "/api/reviews/"
FEED_URL = "/api/feed/"
LOGS_URL = "/api/logs/"


def _query_count(client, url):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx)


@pytest.mark.django_db
class TestReviewListQueryCount:
    def test_no_n_plus_one(self, auth_client):
        """GET /api/reviews/ deve usar queries fixas independente do volume."""
        viewer = UserFactory.create()
        client = auth_client(viewer)

        # Baseline: 3 reviews de diferentes autores/jogos
        for _ in range(3):
            ReviewFactory.create(user=UserFactory.create(), game=GameFactory.create())
        queries_small = _query_count(client, REVIEWS_URL)

        # Escala: mais 7 reviews (10 total visíveis)
        for _ in range(7):
            ReviewFactory.create(user=UserFactory.create(), game=GameFactory.create())
        queries_large = _query_count(client, REVIEWS_URL)

        assert queries_small == queries_large, (
            f"N+1 em /reviews/: {queries_small} queries com 3 itens, "
            f"{queries_large} com 10 itens"
        )

    def test_liked_by_me_no_extra_query(self, auth_client):
        """liked_by_me usa prefetch, não query por review."""
        user = UserFactory.create()
        client = auth_client(user)
        game = GameFactory.create()
        reviews = [ReviewFactory.create(user=UserFactory.create(), game=game) for _ in range(5)]

        # Curtir algumas reviews
        from apps.reviews.models import Like
        for r in reviews[:3]:
            Like.objects.create(user=user, review=r)

        queries_3_likes = _query_count(client, REVIEWS_URL)

        # Curtir todas
        for r in reviews[3:]:
            Like.objects.create(user=user, review=r)

        queries_5_likes = _query_count(client, REVIEWS_URL)

        assert queries_3_likes == queries_5_likes, (
            f"N+1 em liked_by_me: {queries_3_likes} vs {queries_5_likes}"
        )


@pytest.mark.django_db
class TestFeedQueryCount:
    def _setup_feed(self, follower, n_events):
        """Cria n_events de review_created no feed do follower."""
        followed = UserFactory.create()
        Follow.objects.create(follower=follower, following=followed)
        for _ in range(n_events):
            ReviewFactory.create(user=followed, game=GameFactory.create())
        return followed

    def test_no_n_plus_one_review_events(self, auth_client):
        """GET /api/feed/ com eventos de review não deve escalar queries."""
        user = UserFactory.create()
        client = auth_client(user)

        self._setup_feed(user, n_events=3)
        queries_small = _query_count(client, FEED_URL)

        self._setup_feed(user, n_events=7)
        queries_large = _query_count(client, FEED_URL)

        assert queries_small == queries_large, (
            f"N+1 em /feed/ (reviews): {queries_small} queries com ~3 itens, "
            f"{queries_large} com ~10 itens"
        )

    def test_no_n_plus_one_mixed_events(self, auth_client):
        """GET /api/feed/ com eventos mistos não deve escalar queries."""
        user = UserFactory.create()
        client = auth_client(user)

        followed = UserFactory.create()
        Follow.objects.create(follower=user, following=followed)

        # Gera review + log + list events
        for _ in range(3):
            ReviewFactory.create(user=followed, game=GameFactory.create())
            LogFactory.create(user=followed, game=GameFactory.create())
            GameListFactory.create(user=followed)

        queries_small = _query_count(client, FEED_URL)

        for _ in range(4):
            ReviewFactory.create(user=followed, game=GameFactory.create())
            LogFactory.create(user=followed, game=GameFactory.create())
            GameListFactory.create(user=followed)

        queries_large = _query_count(client, FEED_URL)

        assert queries_small == queries_large, (
            f"N+1 em /feed/ (misto): {queries_small} queries com 9 eventos, "
            f"{queries_large} com 21 eventos"
        )


@pytest.mark.django_db
class TestGameLogQueryCount:
    def test_no_n_plus_one(self, auth_client):
        """GET /api/logs/ deve usar queries fixas independente do volume."""
        user = UserFactory.create()
        client = auth_client(user)

        for _ in range(3):
            LogFactory.create(user=user, game=GameFactory.create())
        queries_small = _query_count(client, LOGS_URL)

        for _ in range(7):
            LogFactory.create(user=user, game=GameFactory.create())
        queries_large = _query_count(client, LOGS_URL)

        assert queries_small == queries_large, (
            f"N+1 em /logs/: {queries_small} queries com 3 itens, "
            f"{queries_large} com 10 itens"
        )


@pytest.mark.django_db
class TestFollowersListQueryCount:
    def test_is_following_no_n_plus_one(self, auth_client):
        """GET /api/users/{u}/followers/ não deve fazer query por usuário (is_following)."""
        viewer = UserFactory.create()
        target = UserFactory.create()
        client = auth_client(viewer)

        # 3 seguidores
        followers_small = [UserFactory.create() for _ in range(3)]
        for f in followers_small:
            Follow.objects.create(follower=f, following=target)
            Follow.objects.create(follower=viewer, following=f)  # viewer segue cada um

        url = f"/api/users/{target.username}/followers/"
        queries_small = _query_count(client, url)

        # +7 seguidores (10 total)
        followers_large = [UserFactory.create() for _ in range(7)]
        for f in followers_large:
            Follow.objects.create(follower=f, following=target)
            Follow.objects.create(follower=viewer, following=f)

        queries_large = _query_count(client, url)

        assert queries_small == queries_large, (
            f"N+1 em is_following (/followers/): {queries_small} queries com 3 usuários, "
            f"{queries_large} com 10 usuários"
        )

    def test_following_list_no_n_plus_one(self, auth_client):
        """GET /api/users/{u}/following/ não deve fazer query por usuário."""
        viewer = UserFactory.create()
        target = UserFactory.create()
        client = auth_client(viewer)

        # target segue 3 pessoas; viewer também segue elas
        followed_small = [UserFactory.create() for _ in range(3)]
        for u in followed_small:
            Follow.objects.create(follower=target, following=u)
            Follow.objects.create(follower=viewer, following=u)

        url = f"/api/users/{target.username}/following/"
        queries_small = _query_count(client, url)

        # target segue mais 7
        followed_large = [UserFactory.create() for _ in range(7)]
        for u in followed_large:
            Follow.objects.create(follower=target, following=u)
            Follow.objects.create(follower=viewer, following=u)

        queries_large = _query_count(client, url)

        assert queries_small == queries_large, (
            f"N+1 em is_following (/following/): {queries_small} queries com 3 usuários, "
            f"{queries_large} com 10 usuários"
        )
