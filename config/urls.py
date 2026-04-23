from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls.auth")),
    path("api/users/", include("apps.users.urls.users")),
    path("api/games/", include("apps.games.urls")),
    path("api/reviews/", include("apps.reviews.urls")),
    path("api/logs/", include("apps.activity.urls.logs")),
    path("api/lists/", include("apps.activity.urls.lists")),
    path("api/feed/", include("apps.activity.urls.feed")),
    path("api/health/", include("apps.activity.urls.health")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
