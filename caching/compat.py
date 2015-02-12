import django

__all__ = ['DEFAULT_TIMEOUT', 'FOREVER', 'get_cache']


if django.VERSION[:2] >= (1, 6):
    from django.core.cache.backends.base import DEFAULT_TIMEOUT as DJANGO_DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = DJANGO_DEFAULT_TIMEOUT
    FOREVER = None
else:
    DEFAULT_TIMEOUT = None
    FOREVER = 0


try:
    from django.core.cache import _create_cache
    from django.core import signals

    def get_cache(backend, **kwargs):
        """
        Compatibility wrapper for getting Django's cache backend instance
        """
        cache = _create_cache(backend, **kwargs)
        # Some caches -- python-memcached in particular -- need to do a cleanup
        # at the end of a request cycle. If not implemented in a particular
        # backend, cache.close() is a no-op
        signals.request_finished.connect(cache.close)
        return cache

except ImportError:
    # Django < 1.7
    from django.core.cache import get_cache
