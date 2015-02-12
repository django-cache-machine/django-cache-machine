import datetime
import hashlib
import logging
try:
    unicode = unicode
except NameError:  # 'unicode' is undefined => Python 3
    unicode = str
    bytes = bytes
    basestring = (str, bytes)
else:  # 'unicode' exists => Python 2
    unicode = unicode
    bytes = str
    basestring = basestring

from django.conf import settings
from django.core.cache import cache as default_cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.db.models import Model
from django.utils import encoding, translation

from .compat import get_cache, DEFAULT_TIMEOUT

# Look for an own cache first before falling back to the default cache
try:
    cache = get_cache('cache_machine')
except (InvalidCacheBackendError, ValueError):
    cache = default_cache


CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', '')
FETCH_BY_ID = getattr(settings, 'FETCH_BY_ID', False)
FLUSH = CACHE_PREFIX + ':flush:'

log = logging.getLogger('caching.invalidation')


def make_key(k, with_locale=True):
    """Generate the full key for ``k``, with a prefix."""
    key = encoding.smart_str('%s:%s' % (CACHE_PREFIX, k))
    if with_locale:
        key += encoding.smart_str(translation.get_language())
    # memcached keys must be < 250 bytes and w/o whitespace, but it's nice
    # to see the keys when using locmem.
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def get_root_key(model):
    key = getattr(model, '__caching_root_key', None)
    if not key:
        # In case of inheritance, ensure the base model is always used as the root key.
        classes = [model]
        base_model = model
        while classes:
            class_ = classes.pop(0)
            if issubclass(class_, Model):
                base_model = class_
                classes += list(class_.__bases__)

        key = make_key('caching:root:%s' % hash(base_model))
        model.__caching_root_key = key
    return key


def cache_get(model, key, default=None):
    """
    Retrieves the cache item for the given key.
    A two-layer invalidation scheme is used; the model class is used to generate the final key.

    model: subclass of BaseModel
    key: string
    default: anything or None

    returns: anything or None
    """
    root_key = get_root_key(model)
    prefix = cache.get(root_key)
    if prefix is None:
        return default

    key = make_key(prefix + key)
    return cache.get(key, default=default)


def cache_set(model, key, value, timeout=None, root_key=None, root_timeout=None):
    """
    Sets the cache item for the given key.
    A two-layer invalidation scheme is used; the model class is used to generate the final key.

    model: subclass of BaseModel
    key: string
    value: anything
    timeout: int or None
    root_timeout: int or None

    returns: None
    """
    if root_timeout is None:
        root_timeout = DEFAULT_TIMEOUT
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    root_key = get_root_key(model)
    prefix = cache.get(root_key)
    if prefix is None:
        prefix = datetime.datetime.now().isoformat()
        cache.set(root_key, prefix, root_timeout)

    key = make_key(prefix + key)
    cache.set(key, value, timeout)


def cache_set_many(model, items, timeout=None, root_key=None, root_timeout=None):
    """
    Sets multiple cache key-item pairs.
    A two-layer invalidation scheme is used; the model class is used to generate the final key.

    model: subclass of BaseModel
    items: {key (anythin): value (anything)}
    timeout: int or None
    root_timeout: int or None

    returns: None
    """
    if root_timeout is None:
        root_timeout = DEFAULT_TIMEOUT
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    root_key = make_key('caching:root:%s' % hash(model))
    prefix = cache.get(root_key)
    if prefix is None:
        prefix = datetime.datetime.now().isoformat()
        cache.set(root_key, prefix, root_timeout)

    items = {make_key(prefix + key): value for key, value in items.items()}
    cache.set_many(items, timeout=timeout)


def cache_clear_root(model):
    """
    Clears the root key for the given model.
    """
    root_key = get_root_key(model)
    cache.delete(root_key)


def byid(obj):
    key = obj if isinstance(obj, basestring) else obj.cache_key
    return make_key('byid:' + key)
