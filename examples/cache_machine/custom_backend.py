from .settings import *  # flake8: noqa

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'cache_machine': {
        'BACKEND': 'caching.backends.memcached.PyLibMCCache',
        'LOCATION': 'localhost:11211',
    },
}
