import django

__all__ = ['DEFAULT_TIMEOUT', 'FOREVER', 'get_cache', 'parse_backend_uri']


if django.VERSION[:2] >= (1, 6):
    from django.core.cache.backends.base import DEFAULT_TIMEOUT as DJANGO_DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = DJANGO_DEFAULT_TIMEOUT
    FOREVER = None
else:
    DEFAULT_TIMEOUT = None
    FOREVER = 0


def get_cache(backend, **kwargs):
    """
    Compatibility wrapper for getting Django's cache backend instance
    """
    try:
        from django.core.cache import _create_cache
    except ImportError:
        # Django < 1.7
        from django.core.cache import get_cache as _get_cache
        from django.core import signals
        return _get_cache(backend, **kwargs)

    cache = _create_cache(backend, **kwargs)
    # Some caches -- python-memcached in particular -- need to do a cleanup
    # at the end of a request cycle. If not implemented in a particular
    # backend, cache.close() is a no-op
    signals.request_finished.connect(cache.close)
    return cache


def parse_backend_uri(backend_uri):
    """
    Converts the "backend_uri" into a host and any extra params that are
    required for the backend. Returns a (host, params) tuple.
    """
    try:
        from django.core.cache import parse_backend_uri
        return parse_backend_uri(backend_uri)
    except ImportError:
        from django.utils.six.moves.urllib.parse import parse_qsl
        backend_uri_sliced = backend_uri.split('://')
        if len(backend_uri_sliced) > 2:
            raise InvalidCacheBackendError(
                "Backend URI can't have more than one scheme://")
        elif len(backend_uri_sliced) == 2:
            rest = backend_uri_sliced[1]
        else:
            rest = backend_uri_sliced[0]

        host = rest
        qpos = rest.find('?')
        if qpos != -1:
            params = dict(parse_qsl(rest[qpos+1:]))
            host = rest[:qpos]
        else:
            params = {}
        if host.endswith('/'):
            host = host[:-1]

        return host, params
