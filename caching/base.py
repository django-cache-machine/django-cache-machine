from __future__ import unicode_literals

import functools
import logging

import django
from django.db import models
from django.db.models import signals
from django.db.models.sql import query, EmptyResultSet
from django.utils import encoding

from caching import config
from .compat import DEFAULT_TIMEOUT
from .invalidation import invalidator, flush_key, make_key, byid, cache


class NullHandler(logging.Handler):

    def emit(self, record):
        pass


log = logging.getLogger('caching')
log.addHandler(NullHandler())


class CachingManager(models.Manager):

    # Tell Django to use this manager when resolving foreign keys.
    use_for_related_fields = True

    def get_queryset(self):
        return CachingQuerySet(self.model, using=self._db)

    if django.VERSION < (1, 6):
        get_query_set = get_queryset

    def contribute_to_class(self, cls, name):
        signals.post_save.connect(self.post_save, sender=cls)
        signals.post_delete.connect(self.post_delete, sender=cls)
        return super(CachingManager, self).contribute_to_class(cls, name)

    def post_save(self, instance, **kwargs):
        self.invalidate(instance, is_new_instance=kwargs['created'],
                        model_cls=kwargs['sender'])

    def post_delete(self, instance, **kwargs):
        self.invalidate(instance)

    def invalidate(self, *objects, **kwargs):
        """Invalidate all the flush lists associated with ``objects``."""
        invalidator.invalidate_objects(objects, **kwargs)

    def raw(self, raw_query, params=None, *args, **kwargs):
        return CachingRawQuerySet(raw_query, self.model, params=params,
                                  using=self._db, *args, **kwargs)

    def cache(self, timeout=DEFAULT_TIMEOUT):
        return self.get_queryset().cache(timeout)

    def no_cache(self):
        return self.cache(config.NO_CACHE)


class CacheMachine(object):
    """
    Handles all the cache management for a QuerySet.

    Takes the string representation of a query and a function that can be
    called to get an iterator over some database results.
    """

    def __init__(self, model, query_string, iter_function, timeout=DEFAULT_TIMEOUT, db='default'):
        self.model = model
        self.query_string = query_string
        self.iter_function = iter_function
        self.timeout = timeout
        self.db = db

    def query_key(self):
        """
        Generate the cache key for this query.

        Database router info is included to avoid the scenario where related
        cached objects from one DB (e.g. slave) are saved in another DB (e.g.
        master), throwing a Django ValueError in the process. Django prevents
        cross DB model saving among related objects.
        """
        query_db_string = 'qs:%s::db:%s' % (self.query_string, self.db)
        return make_key(query_db_string, with_locale=False)

    def __iter__(self):
        try:
            query_key = self.query_key()
        except query.EmptyResultSet:
            raise StopIteration

        # Try to fetch from the cache.
        cached = cache.get(query_key)
        if cached is not None:
            log.debug('cache hit: %s' % query_key)
            for obj in cached:
                obj.from_cache = True
                yield obj
            return

        # Do the database query, cache it once we have all the objects.
        iterator = self.iter_function()

        to_cache = []
        try:
            while True:
                obj = next(iterator)
                obj.from_cache = False
                to_cache.append(obj)
                yield obj
        except StopIteration:
            if to_cache or config.CACHE_EMPTY_QUERYSETS:
                self.cache_objects(to_cache, query_key)
            raise

    def cache_objects(self, objects, query_key):
        """Cache query_key => objects, then update the flush lists."""
        log.debug('query_key: %s' % query_key)
        query_flush = flush_key(self.query_string)
        log.debug('query_flush: %s' % query_flush)
        cache.add(query_key, objects, timeout=self.timeout)
        invalidator.cache_objects(self.model, objects, query_key, query_flush)


class CachingQuerySet(models.query.QuerySet):

    _default_timeout_pickle_key = '__DEFAULT_TIMEOUT__'

    def __init__(self, *args, **kw):
        super(CachingQuerySet, self).__init__(*args, **kw)
        self.timeout = DEFAULT_TIMEOUT

    def __getstate__(self):
        """
        Safely pickle our timeout if it's a DEFAULT_TIMEOUT. This is not needed
        by cache-machine itself, but by application code that may re-cache objects
        retrieved using cache-machine.
        """
        state = dict()
        state.update(self.__dict__)
        if self.timeout == DEFAULT_TIMEOUT:
            state['timeout'] = self._default_timeout_pickle_key
        return state

    def __setstate__(self, state):
        """ Safely unpickle our timeout if it's a DEFAULT_TIMEOUT. """
        self.__dict__.update(state)
        if self.timeout == self._default_timeout_pickle_key:
            self.timeout = DEFAULT_TIMEOUT

    def flush_key(self):
        return flush_key(self.query_key())

    def query_key(self):
        clone = self.query.clone()
        sql, params = clone.get_compiler(using=self.db).as_sql()
        return sql % params

    def iterator(self):
        iterator = super(CachingQuerySet, self).iterator
        if self.timeout == config.NO_CACHE:
            return iter(iterator())
        else:
            try:
                # Work-around for Django #12717.
                query_string = self.query_key()
            except query.EmptyResultSet:
                return iterator()
            if config.FETCH_BY_ID:
                iterator = self.fetch_by_id
            return iter(CacheMachine(self.model, query_string, iterator, self.timeout, db=self.db))

    def fetch_by_id(self):
        """
        Run two queries to get objects: one for the ids, one for id__in=ids.

        After getting ids from the first query we can try cache.get_many to
        reuse objects we've already seen.  Then we fetch the remaining items
        from the db, and put those in the cache.  This prevents cache
        duplication.
        """
        # Include columns from extra since they could be used in the query's
        # order_by.
        vals = self.values_list('pk', *list(self.query.extra.keys()))
        pks = [val[0] for val in vals]
        keys = dict((byid(self.model._cache_key(pk, self.db)), pk) for pk in pks)
        cached = dict((k, v) for k, v in list(cache.get_many(keys).items())
                      if v is not None)

        # Pick up the objects we missed.
        missed = [pk for key, pk in list(keys.items()) if key not in cached]
        if missed:
            others = self.fetch_missed(missed)
            # Put the fetched objects back in cache.
            new = dict((byid(o), o) for o in others)
            cache.set_many(new)
        else:
            new = {}

        # Use pks to return the objects in the correct order.
        objects = dict((o.pk, o) for o in list(cached.values()) + list(new.values()))
        for pk in pks:
            yield objects[pk]

    def fetch_missed(self, pks):
        # Reuse the queryset but get a clean query.
        others = self.all()
        others.query.clear_limits()
        # Clear out the default ordering since we order based on the query.
        others = others.order_by().filter(pk__in=pks)
        if hasattr(others, 'no_cache'):
            others = others.no_cache()
        if self.query.select_related:
            others.query.select_related = self.query.select_related
        return others

    def count(self):
        super_count = super(CachingQuerySet, self).count
        try:
            query_string = 'count:%s' % self.query_key()
        except query.EmptyResultSet:
            return 0
        if self.timeout == config.NO_CACHE or config.TIMEOUT == config.NO_CACHE:
            return super_count()
        else:
            return cached_with(self, super_count, query_string, config.TIMEOUT)

    def cache(self, timeout=DEFAULT_TIMEOUT):
        qs = self._clone()
        qs.timeout = timeout
        return qs

    def no_cache(self):
        return self.cache(config.NO_CACHE)

    def _clone(self, *args, **kw):
        qs = super(CachingQuerySet, self)._clone(*args, **kw)
        qs.timeout = self.timeout
        return qs


class CachingMixin(object):
    """Inherit from this class to get caching and invalidation helpers."""

    def flush_key(self):
        return flush_key(self)

    def get_cache_key(self, incl_db=True):
        """Return a cache key based on the object's primary key."""
        # incl_db will be False if this key is intended for use in a flush key.
        # This ensures all cached copies of an object will be invalidated
        # regardless of the DB on which they're modified/deleted.
        return self._cache_key(self.pk, incl_db and self._state.db or None)
    cache_key = property(get_cache_key)

    @classmethod
    def model_flush_key(cls):
        """
        Return a cache key for the entire model (used by invalidation).
        """
        # use dummy PK and DB reference that will never resolve to an actual
        # cache key for an object
        return flush_key(cls._cache_key('all-pks', 'all-dbs'))

    @classmethod
    def _cache_key(cls, pk, db=None):
        """
        Return a string that uniquely identifies the object.

        For the Addon class, with a pk of 2, we get "o:addons.addon:2".
        """
        if db:
            key_parts = ('o', cls._meta, pk, db)
        else:
            key_parts = ('o', cls._meta, pk)
        return ':'.join(map(encoding.smart_text, key_parts))

    def _cache_keys(self, incl_db=True):
        """Return the cache key for self plus all related foreign keys."""
        fks = dict((f, getattr(self, f.attname)) for f in self._meta.fields
                   if isinstance(f, models.ForeignKey))
        keys = [fk.rel.to._cache_key(val, incl_db and self._state.db or None)
                for fk, val in list(fks.items())
                if val is not None and hasattr(fk.rel.to, '_cache_key')]
        return (self.get_cache_key(incl_db=incl_db),) + tuple(keys)

    def _flush_keys(self):
        """Return the flush key for self plus all related foreign keys."""
        return map(flush_key, self._cache_keys(incl_db=False))


class CachingRawQuerySet(models.query.RawQuerySet):

    def __init__(self, *args, **kw):
        timeout = kw.pop('timeout', DEFAULT_TIMEOUT)
        super(CachingRawQuerySet, self).__init__(*args, **kw)
        self.timeout = timeout

    def __iter__(self):
        iterator = super(CachingRawQuerySet, self).__iter__
        if self.timeout == config.NO_CACHE:
            iterator = iterator()
            while True:
                yield next(iterator)
        else:
            sql = self.raw_query % tuple(self.params)
            for obj in CacheMachine(self.model, sql, iterator, timeout=self.timeout):
                yield obj
            raise StopIteration


def _function_cache_key(key):
    return make_key('f:%s' % key, with_locale=True)


def cached(function, key_, duration=DEFAULT_TIMEOUT):
    """Only calls the function if ``key`` is not already in the cache."""
    key = _function_cache_key(key_)
    val = cache.get(key)
    if val is None:
        log.debug('cache miss for %s' % key)
        val = function()
        cache.set(key, val, duration)
    else:
        log.debug('cache hit for %s' % key)
    return val


def cached_with(obj, f, f_key, timeout=DEFAULT_TIMEOUT):
    """Helper for caching a function call within an object's flush list."""

    try:
        obj_key = (obj.query_key() if hasattr(obj, 'query_key')
                   else obj.cache_key)
    except (AttributeError, EmptyResultSet):
        log.warning('%r cannot be cached.' % encoding.smart_text(obj))
        return f()

    key = '%s:%s' % tuple(map(encoding.smart_text, (f_key, obj_key)))
    # Put the key generated in cached() into this object's flush list.
    invalidator.add_to_flush_list(
        {obj.flush_key(): [_function_cache_key(key)]})
    return cached(f, key, timeout)


class cached_method(object):
    """
    Decorator to cache a method call in this object's flush list.

    The external cache will only be used once per (instance, args).  After that
    a local cache on the object will be used.

    Lifted from werkzeug.
    """
    def __init__(self, func):
        self.func = func
        functools.update_wrapper(self, func)

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        _missing = object()
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            w = MethodWrapper(obj, self.func)
            obj.__dict__[self.__name__] = w
            return w
        return value


class MethodWrapper(object):
    """
    Wraps around an object's method for two-level caching.

    The first call for a set of (args, kwargs) will use an external cache.
    After that, an object-local dict cache will be used.
    """
    def __init__(self, obj, func):
        self.obj = obj
        self.func = func
        functools.update_wrapper(self, func)
        self.cache = {}

    def __call__(self, *args, **kwargs):
        k = lambda o: o.cache_key if hasattr(o, 'cache_key') else o
        arg_keys = list(map(k, args))
        kwarg_keys = [(key, k(val)) for key, val in list(kwargs.items())]
        key_parts = ('m', self.obj.cache_key, self.func.__name__,
                     arg_keys, kwarg_keys)
        key = ':'.join(map(encoding.smart_text, key_parts))
        if key not in self.cache:
            f = functools.partial(self.func, self.obj, *args, **kwargs)
            self.cache[key] = cached_with(self.obj, f, key)
        return self.cache[key]
