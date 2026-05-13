import pytest
from rest_framework import status

from tests.factories import FollowFactory, LogFactory, ReviewFactory, UserFactory, GameFactory

PROFILE_URL = "/api/users/{}/"
FOLLOW_URL = "/api/users/{}/follow/"
STATS_URL = "/api/users/me/stats/"


@pytest.mark.django_db
class TestPublicProfile:
    def test_get_profile_exists(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        client = auth_client(user)
        response = client.get(PROFILE_URL.format(target.username))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == target.username

    def test_get_profile_not_found(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        response = client.get(PROFILE_URL.format("nonexistentuser"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_is_following_true(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        FollowFactory.create(follower=user, following=target)
        client = auth_client(user)
        response = client.get(PROFILE_URL.format(target.username))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_following"] is True

    def test_is_following_false(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        client = auth_client(user)
        response = client.get(PROFILE_URL.format(target.username))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_following"] is False


@pytest.mark.django_db
class TestFollow:
    def test_follow_success(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        client = auth_client(user)
        response = client.post(FOLLOW_URL.format(target.username))
        assert response.status_code == status.HTTP_201_CREATED

    def test_follow_self(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        response = client.post(FOLLOW_URL.format(user.username))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_follow_already_following(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        FollowFactory.create(follower=user, following=target)
        client = auth_client(user)
        response = client.post(FOLLOW_URL.format(target.username))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unfollow_success(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        FollowFactory.create(follower=user, following=target)
        client = auth_client(user)
        response = client.delete(FOLLOW_URL.format(target.username))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unfollow_not_following(self, auth_client):
        user = UserFactory.create()
        target = UserFactory.create()
        client = auth_client(user)
        response = client.delete(FOLLOW_URL.format(target.username))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestStats:
    def test_stats_counts_correctly(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)

        game1 = GameFactory.create()
        game2 = GameFactory.create()
        game3 = GameFactory.create()

        LogFactory.create(user=user, game=game1, status="completed")
        LogFactory.create(user=user, game=game2, status="playing")
        ReviewFactory.create(user=user, game=game3)

        follower = UserFactory.create()
        FollowFactory.create(follower=follower, following=user)
        other = UserFactory.create()
        FollowFactory.create(follower=user, following=other)

        response = client.get(STATS_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["saves_count"] == 2
        assert data["completed_count"] == 1
        assert data["playing_count"] == 1
        assert data["reviews_count"] == 1
        assert data["followers_count"] == 1
        assert data["following_count"] == 1
