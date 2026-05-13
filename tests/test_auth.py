import pytest
from rest_framework import status

from tests.factories import UserFactory

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"
REFRESH_URL = "/api/auth/refresh/"


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, api_client):
        data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "strongpass123",
            "password_confirm": "strongpass123",
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["email"] == "newuser@test.com"

    def test_register_duplicate_email(self, api_client):
        user = UserFactory.create(email="taken@test.com")
        data = {
            "username": "another",
            "email": "taken@test.com",
            "password": "strongpass123",
            "password_confirm": "strongpass123",
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, api_client):
        UserFactory.create(username="takenuser")
        data = {
            "username": "takenuser",
            "email": "unique@test.com",
            "password": "strongpass123",
            "password_confirm": "strongpass123",
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client):
        data = {
            "username": "mismatch",
            "email": "mismatch@test.com",
            "password": "strongpass123",
            "password_confirm": "differentpass",
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        data = {
            "username": "weakuser",
            "email": "weak@test.com",
            "password": "short",
            "password_confirm": "short",
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client):
        UserFactory.create(email="login@test.com")
        response = api_client.post(LOGIN_URL, {"email": "login@test.com", "password": "testpass123"})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client):
        UserFactory.create(email="wrongpass@test.com")
        response = api_client.post(LOGIN_URL, {"email": "wrongpass@test.com", "password": "wrongpass"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post(LOGIN_URL, {"email": "noone@test.com", "password": "pass12345"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogout:
    def test_logout_success(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = str(RefreshToken.for_user(user))
        response = client.post(LOGOUT_URL, {"refresh_token": refresh})
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_without_auth(self, api_client):
        response = api_client.post(LOGOUT_URL, {"refresh_token": "invalid"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_success(self, api_client):
        user = UserFactory.create()
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = str(RefreshToken.for_user(user))
        response = api_client.post(REFRESH_URL, {"refresh": refresh})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_invalid_token(self, api_client):
        response = api_client.post(REFRESH_URL, {"refresh": "notavalidtoken"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
