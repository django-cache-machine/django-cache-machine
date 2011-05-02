from settings import *

CACHES = {
    'default': {
        'BACKEND': 'caching.backends.locmem.CacheClass',
    },
}
