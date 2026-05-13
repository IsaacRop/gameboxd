from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="reviews.Review")
def on_review_saved(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.activity.models import ActivityFeed
    ActivityFeed.objects.create(
        user=instance.user,
        event_type=ActivityFeed.REVIEW_CREATED,
        review=instance,
    )


@receiver(post_save, sender="activity.Log")
def on_log_saved(sender, instance, **kwargs):
    from apps.activity.models import ActivityFeed
    ActivityFeed.objects.create(
        user=instance.user,
        event_type=ActivityFeed.LOG_UPDATED,
        game_log=instance,
    )


@receiver(post_save, sender="activity.List")
def on_list_saved(sender, instance, created, **kwargs):
    if not created or not instance.is_public:
        return
    from apps.activity.models import ActivityFeed
    ActivityFeed.objects.create(
        user=instance.user,
        event_type=ActivityFeed.LIST_CREATED,
        game_list=instance,
    )


@receiver(post_save, sender="users.Follow")
def on_follow_saved(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.activity.models import ActivityFeed
    ActivityFeed.objects.create(
        user=instance.follower,
        event_type=ActivityFeed.FOLLOW,
        followed_user=instance.following,
    )
