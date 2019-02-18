import os

import django

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
    },
}

TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

DATABASES = {
    'default': {
        'NAME': os.environ.get('TRAVIS') and 'travis_ci_test' or 'cache_machine_devel',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
    },
    'slave': {
        'NAME': 'cache_machine_devel',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'TEST_MIRROR': 'default',  # support older Django syntax for now
    },
    'master2': {
        'NAME': os.environ.get('TRAVIS') and 'travis_ci_test2' or 'cache_machine_devel2',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
    },
    'slave2': {
        'NAME': 'cache_machine_devel2',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'TEST_MIRROR': 'master2',  # support older Django syntax for now
    },
}

INSTALLED_APPS = (
    'django_nose',
    'tests.testapp',
)

SECRET_KEY = 'ok'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

if django.VERSION[0] >= 2:
    MIDDLEWARE = MIDDLEWARE_CLASSES
