import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models


class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    igdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    cover_url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    genres = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    platforms = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games_game"
        ordering = ["title"]

    def __str__(self):
        return self.title
