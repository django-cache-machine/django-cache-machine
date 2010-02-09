CACHE_BACKEND = 'caching.backends.memcached://localhost:11211'

TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django_nose',
)
