import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

from apps.games.models import Game
from apps.reviews.models import Review
from apps.activity.models import List, Log
from apps.users.models import Follow

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@test.com")
    bio = factory.Faker("text", max_nb_chars=100)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or "testpass123")
        self.save(update_fields=["password"])


class GameFactory(DjangoModelFactory):
    class Meta:
        model = Game

    igdb_id = factory.Sequence(lambda n: n + 1)
    title = factory.Sequence(lambda n: f"Game Title {n}")
    slug = factory.Sequence(lambda n: f"game-slug-{n}")
    cover_url = factory.Faker("url")
    summary = factory.Faker("text")
    genres = factory.LazyFunction(lambda: ["RPG", "Action"])
    platforms = factory.LazyFunction(lambda: ["PS5", "PC"])
    rating = factory.Faker("pyfloat", min_value=1, max_value=5, right_digits=1)


class ReviewFactory(DjangoModelFactory):
    class Meta:
        model = Review

    user = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameFactory)
    rating = factory.Faker("random_int", min=1, max=5)
    body = factory.Faker("text", max_nb_chars=500)
    contains_spoiler = False


class LogFactory(DjangoModelFactory):
    class Meta:
        model = Log

    user = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameFactory)
    status = "playing"


class GameListFactory(DjangoModelFactory):
    class Meta:
        model = List

    user = factory.SubFactory(UserFactory)
    title = factory.Faker("catch_phrase")
    is_public = True


class FollowFactory(DjangoModelFactory):
    class Meta:
        model = Follow

    follower = factory.SubFactory(UserFactory)
    following = factory.SubFactory(UserFactory)
