from .settings import *  # flake8: noqa

CACHES = {
    'default': {
        'BACKEND': 'caching.backends.locmem.LocMemCache',
    },
}
