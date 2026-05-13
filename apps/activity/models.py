import uuid
from django.db import models
from django.conf import settings
from apps.games.models import Game


class Log(models.Model):
    STATUS_CHOICES = [
        ("playing", "Playing"),
        ("completed", "Completed"),
        ("dropped", "Dropped"),
        ("want_to_play", "Want to Play"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="logs", on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name="logs", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    played_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "activity_log"
        unique_together = ("user", "game")

    def __str__(self):
        return f"{self.user} → {self.game} ({self.status})"


class List(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="lists", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "activity_list"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class ListGame(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    list = models.ForeignKey(List, related_name="games", on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name="in_lists", on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "activity_listgame"
        unique_together = ("list", "game")
        ordering = ["position"]


class Activity(models.Model):
    VERB_CHOICES = [
        ("reviewed", "Reviewed"),
        ("logged", "Logged"),
        ("liked", "Liked"),
        ("followed", "Followed"),
        ("listed", "Listed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="activities", on_delete=models.CASCADE)
    verb = models.CharField(max_length=20, choices=VERB_CHOICES)
    object_type = models.CharField(max_length=20)
    object_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_activity"
        ordering = ["-created_at"]
