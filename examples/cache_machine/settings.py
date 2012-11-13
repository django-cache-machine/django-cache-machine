CACHES = {
    'default': {
        'BACKEND': 'caching.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
    },
}

TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

DATABASES = {
    'default': {
        'NAME': ':memory:',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django_nose',
)

SECRET_KEY = 'ok'
