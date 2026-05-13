import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def auth_client(api_client):
    def _make(user):
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client
    return _make
