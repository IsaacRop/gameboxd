from django.urls import path

from apps.users.views import (
    FollowersListView,
    FollowingListView,
    FollowView,
    MeView,
    PublicProfileView,
    StatsView,
)

urlpatterns = [
    # me/* antes de <username>/ para não colidir
    path("me/", MeView.as_view(), name="user-me"),
    path("me/stats/", StatsView.as_view(), name="user-stats"),
    path("<str:username>/", PublicProfileView.as_view(), name="user-profile"),
    path("<str:username>/follow/", FollowView.as_view(), name="user-follow"),
    path("<str:username>/followers/", FollowersListView.as_view(), name="user-followers"),
    path("<str:username>/following/", FollowingListView.as_view(), name="user-following"),
]
