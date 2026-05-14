from .base import *  # noqa
import sentry_sdk

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# SECURE_SSL_REDIRECT = True   # Railway já força HTTPS no proxy
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
sentry_sdk.init(dsn=env("SENTRY_DSN", default=""))  # noqa
