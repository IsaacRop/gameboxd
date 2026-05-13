import uuid
from django.db import models
from django.conf import settings
from apps.games.models import Game


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reviews", on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name="reviews", on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=2, decimal_places=1)
    body = models.TextField(blank=True)
    contains_spoiler = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews_review"
        unique_together = ("user", "game")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.game} ({self.rating})"


class Like(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="likes", on_delete=models.CASCADE)
    review = models.ForeignKey(Review, related_name="likes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews_like"
        unique_together = ("user", "review")
