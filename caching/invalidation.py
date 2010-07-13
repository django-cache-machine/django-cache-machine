import collections
import hashlib

from django.conf import settings
from django.core.cache import cache, parse_backend_uri
from django.utils import encoding, translation


CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', '')
FLUSH = CACHE_PREFIX + ':flush:'


def make_key(k, with_locale=True):
    """Generate the full key for ``k``, with a prefix."""
    key = '%s:%s' % (CACHE_PREFIX, k)
    if with_locale:
        key += translation.get_language()
    # memcached keys must be < 250 bytes and w/o whitespace, but it's nice
    # to see the keys when using locmem.
    if 'memcached' in cache.scheme:
        return hashlib.md5(encoding.smart_str(key)).hexdigest()
    else:
        return key


def flush_key(obj):
    """We put flush lists in the flush: namespace."""
    key = obj if isinstance(obj, basestring) else obj.cache_key
    return FLUSH + make_key(key, with_locale=False)


class Invalidator(object):

    def invalidate_keys(self, keys):
        """Invalidate all the flush lists named by the list of ``keys``."""
        if not keys:
            return
        flush, flush_keys = self.find_flush_lists(keys)

        if flush:
            cache.set_many(dict((k, None) for k in flush), 5)
        if flush_keys:
            self.clear_flush_lists(flush_keys)

    def cache_objects(self, objects, query_key, query_flush):
        # Add this query to the flush list of each object.  We include
        # query_flush so that other things can be cached against the queryset
        # and still participate in invalidation.
        flush_keys = [o.flush_key() for o in objects]

        flush_lists = collections.defaultdict(set)
        for key in flush_keys:
            flush_lists[key].add(query_flush)
        flush_lists[query_flush].add(query_key)

        # Add each object to the flush lists of its foreign keys.
        for obj in objects:
            obj_flush = obj.flush_key()
            for key in map(flush_key, obj._cache_keys()):
                if key != obj_flush:
                    flush_lists[key].add(obj_flush)
        self.add_to_flush_list(flush_lists)

    def find_flush_lists(self, keys):
        """
        Recursively search for flush lists and objects to invalidate.

        The search starts with the lists in `keys` and expands to any flush
        lists found therein.  Returns ({objects to flush}, {flush keys found}).
        """
        new_keys = keys = set(map(flush_key, keys))
        flush = set(keys)

        # Add other flush keys from the lists, which happens when a parent
        # object includes a foreign key.
        while 1:
            to_flush = self.get_flush_lists(new_keys)
            flush.update(to_flush)
            new_keys = set(k for k in to_flush if k.startswith(FLUSH))
            diff = new_keys.difference(keys)
            if diff:
                keys.update(new_keys)
            else:
                return flush, keys

    def add_to_flush_list(self, mapping):
        """Update flush lists with the {flush_key: [query_key,...]} map."""
        flush_lists = collections.defaultdict(set)
        flush_lists.update(cache.get_many(mapping.keys()))
        for key, list_ in mapping.items():
            if flush_lists[key] is None:
                flush_lists[key] = set(list_)
            else:
                flush_lists[key].update(list_)
        cache.set_many(flush_lists)

    def get_flush_lists(self, keys):
        """Return a set of object keys from the lists in `keys`."""
        return set(e for flush_list in cache.get_many(keys).values()
                     for e in flush_list)

    def clear_flush_lists(self, keys):
        """Remove the given keys from the database."""
        cache.delete_many(keys)


class RedisInvalidator(Invalidator):

    def add_to_flush_list(self, mapping):
        """Update flush lists with the {flush_key: [query_key,...]} map."""
        pipe = redis.pipeline(transaction=False)
        for key, list_ in mapping.items():
            for query_key in list_:
                pipe.sadd(key, query_key)
        pipe.execute()

    def get_flush_lists(self, keys):
        return redis.sunion(keys)

    def clear_flush_lists(self, keys):
        redis.delete(*keys)


def get_redis_backend():
    """Connect to redis from a string like CACHE_BACKEND."""
    # From django-redis-cache.
    import redis
    _, server, params = parse_backend_uri(settings.REDIS_BACKEND)
    db = params.get('db', 1)
    try:
        db = int(db)
    except (ValueError, TypeError):
        db = 1
    password = params.get('password', None)
    if ':' in server:
        host, port = server.split(':')
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = 6379
    else:
        host = 'localhost'
        port = 6379
    return redis.Redis(host=host, port=port, db=db, password=password)


if getattr(settings, 'CACHE_MACHINE_USE_REDIS', False):
    redis = get_redis_backend()
    invalidator = RedisInvalidator()
else:
    invalidator = Invalidator()
