from .base import *  # noqa
DEBUG = True
INSTALLED_APPS += ["silk", "django_extensions"]  # noqa
MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]  # noqa
