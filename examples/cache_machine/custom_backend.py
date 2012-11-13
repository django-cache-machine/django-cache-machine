from settings import *

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.CacheClass',
    },
    'cache_machine': {
        'BACKEND': 'caching.backends.memcached.CacheClass',
        'LOCATION': 'localhost:11211',
    },
}
