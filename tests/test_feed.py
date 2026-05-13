import pytest
from rest_framework import status

from apps.users.models import Follow
from tests.factories import (
    FollowFactory,
    GameFactory,
    GameListFactory,
    LogFactory,
    ReviewFactory,
    UserFactory,
)

FEED_URL = "/api/feed/"


@pytest.mark.django_db
class TestFeed:
    def test_feed_shows_followed_activity(self, auth_client):
        user_a = UserFactory.create()
        user_b = UserFactory.create()
        Follow.objects.create(follower=user_a, following=user_b)
        ReviewFactory.create(user=user_b, game=GameFactory.create())
        client = auth_client(user_a)
        response = client.get(FEED_URL)
        assert response.status_code == status.HTTP_200_OK
        review_events = [
            e for e in response.data["results"]
            if e["event_type"] == "review_created"
        ]
        assert len(review_events) >= 1

    def test_feed_empty_when_not_following(self, auth_client):
        user = UserFactory.create()
        ReviewFactory.create(user=UserFactory.create(), game=GameFactory.create())
        client = auth_client(user)
        response = client.get(FEED_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_feed_excludes_own_activity(self, auth_client):
        user = UserFactory.create()
        ReviewFactory.create(user=user, game=GameFactory.create())
        client = auth_client(user)
        response = client.get(FEED_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_feed_excludes_private_lists(self, auth_client):
        user_a = UserFactory.create()
        user_b = UserFactory.create()
        Follow.objects.create(follower=user_a, following=user_b)
        GameListFactory.create(user=user_b, is_public=True)
        GameListFactory.create(user=user_b, is_public=False)
        client = auth_client(user_a)
        response = client.get(FEED_URL)
        assert response.status_code == status.HTTP_200_OK
        list_events = [
            e for e in response.data["results"]
            if e["event_type"] == "list_created"
        ]
        assert len(list_events) == 1
