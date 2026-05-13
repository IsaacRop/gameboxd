import pytest
from rest_framework import status

from tests.factories import GameFactory, LogFactory, UserFactory

LOGS_URL = "/api/logs/"
LOG_DETAIL_URL = "/api/logs/{}/"


@pytest.mark.django_db
class TestGameLog:
    def test_create_log_success(self, auth_client):
        user = UserFactory.create()
        game = GameFactory.create()
        client = auth_client(user)
        data = {"game": str(game.id), "status": "playing"}
        response = client.post(LOGS_URL, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "playing"
        assert response.data["game"]["title"] == game.title

    def test_create_log_duplicate(self, auth_client):
        user = UserFactory.create()
        game = GameFactory.create()
        LogFactory.create(user=user, game=game)
        client = auth_client(user)
        data = {"game": str(game.id), "status": "completed"}
        response = client.post(LOGS_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_status(self, auth_client):
        user = UserFactory.create()
        game = GameFactory.create()
        log = LogFactory.create(user=user, game=game, status="playing")
        client = auth_client(user)
        response = client.patch(LOG_DETAIL_URL.format(log.id), {"status": "completed"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "completed"

    def test_logs_are_private(self, auth_client):
        owner = UserFactory.create()
        other = UserFactory.create()
        log = LogFactory.create(user=owner, game=GameFactory.create())
        client = auth_client(other)
        response = client.get(LOG_DETAIL_URL.format(log.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_by_status(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        LogFactory.create(user=user, game=GameFactory.create(), status="completed")
        LogFactory.create(user=user, game=GameFactory.create(), status="playing")
        response = client.get(LOGS_URL, {"status": "completed"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["status"] == "completed"
