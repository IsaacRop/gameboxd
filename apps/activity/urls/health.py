from django.urls import path
from django.http import JsonResponse
from django.db import connection


def health(request):
    return JsonResponse({"status": "ok"})


def health_db(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok", "db": "connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "db": str(e)}, status=503)


urlpatterns = [
    path("", health, name="health"),
    path("db/", health_db, name="health_db"),
]
