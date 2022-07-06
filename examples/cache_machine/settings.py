import os

import dj_database_url
import django

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
        "LOCATION": "localhost:11211",
    },
}

DATABASES = {
    "default": dj_database_url.config(default="postgres:///cache_machine_devel"),
    "primary2": dj_database_url.parse(
        os.getenv("DATABASE_URL_2", "postgres:///cache_machine_devel2")
    ),
}
for primary, replica in (("default", "replica"), ("primary2", "replica2")):
    DATABASES[replica] = DATABASES[primary].copy()
    DATABASES[replica]["TEST"] = {"MIRROR": primary}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

INSTALLED_APPS = ("tests.testapp",)

SECRET_KEY = "ok"

MIDDLEWARE_CLASSES = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.SessionAuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

if django.VERSION[0] >= 2:
    MIDDLEWARE = MIDDLEWARE_CLASSES
