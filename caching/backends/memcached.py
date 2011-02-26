from django.core.cache.backends import memcached
from django.utils.encoding import smart_str


# Add infinite timeout support to the memcached backend.
class CacheClass(memcached.CacheClass):

    def add(self, key, value, timeout=None, version=None):
        if timeout is None:
            timeout = self.default_timeout
        return super(CacheClass, self).add(key, value, timeout, version)

    def set(self, key, value, timeout=None, version=None):
        if timeout is None:
            timeout = self.default_timeout
        return super(CacheClass, self).set(key, value, timeout, version)
