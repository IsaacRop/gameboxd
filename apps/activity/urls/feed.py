from django.urls import path

from apps.activity.views import FeedView

urlpatterns = [
    path("", FeedView.as_view(), name="feed"),
]
