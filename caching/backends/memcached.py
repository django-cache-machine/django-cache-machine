import django
from django.core.cache.backends import memcached


# Add infinite timeout support to the memcached backend.
class InfinityMixin(object):

    def add(self, key, value, timeout=None, version=None):
        if timeout is None:
            timeout = self.default_timeout
        return super(InfinityMixin, self).add(key, value, timeout, version)

    def set(self, key, value, timeout=None, version=None):
        if timeout is None:
            timeout = self.default_timeout
        return super(InfinityMixin, self).set(key, value, timeout, version)


class CacheClass(InfinityMixin, memcached.CacheClass):
    pass

if django.VERSION[:2] >= (1, 3):

    class MemcachedCache(InfinityMixin, memcached.MemcachedCache):
        pass

    class PyLibMCCache(InfinityMixin, memcached.PyLibMCCache):
        pass
