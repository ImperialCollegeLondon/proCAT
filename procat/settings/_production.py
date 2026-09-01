"""Settings for app deployment in production.

This module contains those settings that are not expected to vary between
deployments. This module is not intended to be used directly but imported into another
module where deployment specific settings are set.

ADMINS and ALLOWED_HOSTS need to be defined in the deployment specific settings module.
"""

import os

from .settings import *  # noqa: F403

DEBUG = False
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 15552000
USE_X_FORWARDED_HOST = True
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smarthost.cc.ic.ac.uk"
SERVER_EMAIL = "noreply@imperial.ac.uk"
DEFAULT_FROM_EMAIL = SERVER_EMAIL

# Trusted origins for CSRF; comma-separated list of scheme+host values.
# Defaults to localhost for local production-like runs.
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost").split(
    ","
)
