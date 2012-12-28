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
    },
    'slave': {
        'NAME': 'test_slave.db',
        'ENGINE': 'django.db.backends.sqlite3',
        }
}

INSTALLED_APPS = (
    'django_nose',
    'tests.testapp',
)

SECRET_KEY = 'ok'
