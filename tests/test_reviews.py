import pytest
from rest_framework import status

from tests.factories import GameFactory, ReviewFactory, UserFactory

REVIEWS_URL = "/api/reviews/"
REVIEW_DETAIL_URL = "/api/reviews/{}/"
LIKE_URL = "/api/reviews/{}/like/"


@pytest.mark.django_db
class TestCreateReview:
    def test_create_review_success(self, auth_client):
        user = UserFactory.create()
        game = GameFactory.create()
        client = auth_client(user)
        data = {"game": str(game.id), "rating": 4, "body": "Great game!", "contains_spoiler": False}
        response = client.post(REVIEWS_URL, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["rating"] == 4

    def test_create_review_duplicate(self, auth_client):
        user = UserFactory.create()
        game = GameFactory.create()
        ReviewFactory.create(user=user, game=game)
        client = auth_client(user)
        data = {"game": str(game.id), "rating": 3, "body": "Another review", "contains_spoiler": False}
        response = client.post(REVIEWS_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_review_invalid_rating(self, auth_client):
        user = UserFactory.create()
        game = GameFactory.create()
        client = auth_client(user)
        data = {"game": str(game.id), "rating": 6, "body": "Too high rating", "contains_spoiler": False}
        response = client.post(REVIEWS_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_review_unauthenticated(self, api_client):
        game = GameFactory.create()
        data = {"game": str(game.id), "rating": 4, "body": "No auth"}
        response = api_client.post(REVIEWS_URL, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestReviewFilters:
    def test_filter_by_rating(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        reviewer = UserFactory.create()
        ReviewFactory.create(user=reviewer, game=GameFactory.create(), rating=5)
        ReviewFactory.create(user=reviewer, game=GameFactory.create(), rating=3)
        response = client.get(REVIEWS_URL, {"rating": 5})
        assert response.status_code == status.HTTP_200_OK
        assert all(r["rating"] == 5 for r in response.data["results"])

    def test_filter_by_game(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        game1 = GameFactory.create()
        game2 = GameFactory.create()
        reviewer = UserFactory.create()
        ReviewFactory.create(user=reviewer, game=game1)
        ReviewFactory.create(user=UserFactory.create(), game=game2)
        response = client.get(REVIEWS_URL, {"game": str(game1.id)})
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["game"]["id"] == str(game1.id)

    def test_search_by_body(self, auth_client):
        user = UserFactory.create()
        client = auth_client(user)
        reviewer = UserFactory.create()
        ReviewFactory.create(user=reviewer, game=GameFactory.create(), body="incredible masterpiece")
        ReviewFactory.create(user=UserFactory.create(), game=GameFactory.create(), body="average game")
        response = client.get(REVIEWS_URL, {"search": "masterpiece"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert "masterpiece" in results[0]["body"]


@pytest.mark.django_db
class TestLike:
    def test_like_success(self, auth_client):
        user = UserFactory.create()
        reviewer = UserFactory.create()
        review = ReviewFactory.create(user=reviewer, game=GameFactory.create())
        client = auth_client(user)
        response = client.post(LIKE_URL.format(review.id))
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["likes_count"] == 1

    def test_like_own_review(self, auth_client):
        user = UserFactory.create()
        review = ReviewFactory.create(user=user, game=GameFactory.create())
        client = auth_client(user)
        response = client.post(LIKE_URL.format(review.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_like_twice(self, auth_client):
        user = UserFactory.create()
        reviewer = UserFactory.create()
        review = ReviewFactory.create(user=reviewer, game=GameFactory.create())
        client = auth_client(user)
        client.post(LIKE_URL.format(review.id))
        response = client.post(LIKE_URL.format(review.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unlike_success(self, auth_client):
        user = UserFactory.create()
        reviewer = UserFactory.create()
        review = ReviewFactory.create(user=reviewer, game=GameFactory.create())
        client = auth_client(user)
        client.post(LIKE_URL.format(review.id))
        response = client.delete(LIKE_URL.format(review.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestPermissions:
    def test_edit_own_review(self, auth_client):
        user = UserFactory.create()
        review = ReviewFactory.create(user=user, game=GameFactory.create(), rating=3)
        client = auth_client(user)
        response = client.patch(REVIEW_DETAIL_URL.format(review.id), {"rating": 5})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["rating"] == 5

    def test_edit_other_review(self, auth_client):
        owner = UserFactory.create()
        other = UserFactory.create()
        review = ReviewFactory.create(user=owner, game=GameFactory.create())
        client = auth_client(other)
        response = client.patch(REVIEW_DETAIL_URL.format(review.id), {"rating": 1})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_own_review(self, auth_client):
        user = UserFactory.create()
        review = ReviewFactory.create(user=user, game=GameFactory.create())
        client = auth_client(user)
        response = client.delete(REVIEW_DETAIL_URL.format(review.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_other_review(self, auth_client):
        owner = UserFactory.create()
        other = UserFactory.create()
        review = ReviewFactory.create(user=owner, game=GameFactory.create())
        client = auth_client(other)
        response = client.delete(REVIEW_DETAIL_URL.format(review.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN
