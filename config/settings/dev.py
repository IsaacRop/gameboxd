from .base import *  # noqa

DEBUG = True
INSTALLED_APPS += ["silk", "django_extensions"]  # noqa
MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]  # noqa

SPECTACULAR_SETTINGS = {
    **SPECTACULAR_SETTINGS,  # noqa
    "DISABLE_ERRORS_AND_WARNINGS": True,
}
