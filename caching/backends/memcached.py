from __future__ import unicode_literals

import django
from django.core.cache.backends import memcached

from caching.compat import DEFAULT_TIMEOUT


# Add infinite timeout support to the memcached backend, if needed.
class InfinityMixin(object):

    if django.VERSION[:2] < (1, 6):
        # Django 1.6 and later do it the right way already
        def _get_memcache_timeout(self, timeout):
            if timeout == 0:
                return timeout
            else:
                return super(InfinityMixin, self)._get_memcache_timeout(timeout)

        def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
            return super(InfinityMixin, self).add(key, value, timeout, version)

        def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
            return super(InfinityMixin, self).set(key, value, timeout, version)


class MemcachedCache(InfinityMixin, memcached.MemcachedCache):
    pass


class PyLibMCCache(InfinityMixin, memcached.PyLibMCCache):
    pass
