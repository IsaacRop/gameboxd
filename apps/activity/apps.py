from django.apps import AppConfig


class ActivityConfig(AppConfig):
    name = "apps.activity"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import apps.activity.signals  # noqa
