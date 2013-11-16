from settings import *

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'cache_machine': {
        'BACKEND': 'caching.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
    },
}
