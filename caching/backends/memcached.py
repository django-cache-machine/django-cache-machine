import django
from django.core.cache.backends import memcached

from caching.compat import DEFAULT_TIMEOUT


# Add infinite timeout support to the memcached backend.
class InfinityMixin(object):

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return super(InfinityMixin, self).add(key, value, timeout, version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return super(InfinityMixin, self).set(key, value, timeout, version)


if django.VERSION[:2] >= (1, 3):
    class MemcachedCache(InfinityMixin, memcached.MemcachedCache):
        pass

    class PyLibMCCache(InfinityMixin, memcached.PyLibMCCache):
        pass

    class CacheClass(MemcachedCache):
        pass
else:
    class CacheClass(InfinityMixin, memcached.CacheClass):
        pass
