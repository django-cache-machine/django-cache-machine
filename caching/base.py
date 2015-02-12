import functools
import logging

import django
from django.conf import settings
from django.db import models
from django.db.models import signals
from django.db.models.sql import query, EmptyResultSet
from django.utils import encoding

from .compat import DEFAULT_TIMEOUT, FOREVER
from .invalidation import cache_get, cache_set, cache_set_many, cache_clear_root, make_key, byid, cache


class NullHandler(logging.Handler):

    def emit(self, record):
        pass


log = logging.getLogger('caching')
log.addHandler(NullHandler())

NO_CACHE = -1
CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', '')
FETCH_BY_ID = getattr(settings, 'FETCH_BY_ID', False)
CACHE_EMPTY_QUERYSETS = getattr(settings, 'CACHE_EMPTY_QUERYSETS', False)
TIMEOUT = getattr(settings, 'CACHE_COUNT_TIMEOUT', NO_CACHE)


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
        for m2m in cls._meta.many_to_many:
            signals.m2m_changed.connect(self.m2m_changed, sender=m2m.rel.through)
        return super(CachingManager, self).contribute_to_class(cls, name)

    def post_save(self, instance, **kwargs):
        self.invalidate(instance)

    def post_delete(self, instance, **kwargs):
        self.invalidate(instance)

    def m2m_changed(self, action, sender, **kwargs):
        if action.startswith('post_'):
            self.invalidate(model=sender)

    def bulk_create(self, *args, **kwargs):
        result = super(CachingManager, self).bulk_create(*args, **kwargs)
        self.invalidate()
        return result

    def invalidate(self, *objects, **kwargs):
        """Invalidate the root key associated with the model class."""
        base_model = kwargs.get('model') or self.model

        models_to_clear = getattr(base_model, '__caching_related_models_to_clear', None)
        if models_to_clear is None:
            # Also invalidate related models, because their cached queries might include related lookups to this model.
            models_to_clear = [base_model]
            i = 0
            while i < len(models_to_clear):
                model = models_to_clear[i]
                i += 1
                for f in model._meta.fields:
                    if f.rel and issubclass(f.rel.to, CachingMixin) and f.rel.to not in models_to_clear:
                        models_to_clear.append(f.rel.to)
                for f in model._meta.many_to_many:
                    if issubclass(f.rel.to, CachingMixin) and f.rel.to not in models_to_clear:
                        models_to_clear.append(f.rel.to)
                    if issubclass(f.rel.through, CachingMixin) and f.rel.through not in models_to_clear:
                        models_to_clear.append(f.rel.through)

            # Cache the models list (using a class variable, not Django's cache!).
            base_model.__caching_related_models_to_clear = models_to_clear

        # Clear caches.
        for m in models_to_clear:
            cache_clear_root(m)

    def raw(self, raw_query, params=None, *args, **kwargs):
        return CachingRawQuerySet(raw_query, self.model, params=params,
                                  using=self._db, *args, **kwargs)

    def cache(self, timeout=DEFAULT_TIMEOUT):
        return self.get_queryset().cache(timeout)

    def no_cache(self):
        return self.cache(NO_CACHE)


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
        query_db_string = u'qs:%s::db:%s' % (self.query_string, self.db)
        return make_key(query_db_string, with_locale=False)

    def __iter__(self):
        try:
            query_key = self.query_key()
        except query.EmptyResultSet:
            raise StopIteration

        # Try to fetch from the cache.
        cached = cache_get(self.model, query_key)
        if cached is not None:
            log.debug('cache hit: %s' % self.query_string)
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
            if to_cache or CACHE_EMPTY_QUERYSETS:
                self.cache_objects(to_cache)
            raise

    def cache_objects(self, objects):
        """Cache query_key => objects, then update the flush lists."""
        query_key = self.query_key()
        cache_set(self.model, query_key, objects, timeout=self.timeout)


class CachingQuerySet(models.query.QuerySet):

    def __init__(self, *args, **kw):
        super(CachingQuerySet, self).__init__(*args, **kw)
        self.timeout = DEFAULT_TIMEOUT

    @property
    def root_key(self):
        return hash(self.model)

    def query_key(self):
        clone = self.query.clone()
        sql, params = clone.get_compiler(using=self.db).as_sql()
        return hash(sql % params)

    def iterator(self):
        iterator = super(CachingQuerySet, self).iterator
        if self.timeout == NO_CACHE:
            return iter(iterator())
        else:
            try:
                # Work-around for Django #12717.
                query_string = self.query_key()
            except query.EmptyResultSet:
                return iterator()
            if FETCH_BY_ID:
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
        vals = self.values_list('pk', *self.query.extra.keys())
        pks = [val[0] for val in vals]
        keys = dict((byid(self.model._cache_key(pk, self.db)), pk) for pk in pks)
        cached = dict((k, v) for k, v in cache.get_many(keys).items()
                      if v is not None)

        # Pick up the objects we missed.
        missed = [pk for key, pk in keys.items() if key not in cached]
        if missed:
            others = self.fetch_missed(missed)
            # Put the fetched objects back in cache.
            new = dict((byid(o), o) for o in others)
            cache_set_many(self.model, new)
        else:
            new = {}

        # Use pks to return the objects in the correct order.
        objects = dict((o.pk, o) for o in cached.values() + new.values())
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
        if self.timeout == NO_CACHE or TIMEOUT == NO_CACHE:
            return super_count()
        else:
            return cached_with(self.model, self, super_count, query_string, TIMEOUT)

    def cache(self, timeout=DEFAULT_TIMEOUT):
        qs = self._clone()
        qs.timeout = timeout
        return qs

    def no_cache(self):
        return self.cache(NO_CACHE)

    def _clone(self, *args, **kw):
        qs = super(CachingQuerySet, self)._clone(*args, **kw)
        qs.timeout = self.timeout
        return qs


class CachingMixin(object):
    """Inherit from this class to get caching and invalidation helpers."""

    @property
    def cache_key(self):
        """Return a cache key based on the object's primary key."""
        return self._cache_key(self.pk, self._state.db)

    @classmethod
    def _cache_key(cls, pk, db):
        """
        Return a string that uniquely identifies the object.

        For the Addon class, with a pk of 2, we get "o:addons.addon:2".
        """
        key_parts = ('o', cls._meta, pk, db)
        return ':'.join(map(encoding.smart_text, key_parts))

    def _cache_keys(self):
        """Return the cache key for self plus all related foreign keys."""
        fks = dict((f, getattr(self, f.attname)) for f in self._meta.fields
                   if isinstance(f, models.ForeignKey))

        keys = [fk.rel.to._cache_key(val, self._state.db) for fk, val in fks.items()
                if val is not None and hasattr(fk.rel.to, '_cache_key')]
        return (self.cache_key,) + tuple(keys)


class CachingRawQuerySet(models.query.RawQuerySet):

    def __init__(self, *args, **kw):
        timeout = kw.pop('timeout', DEFAULT_TIMEOUT)
        super(CachingRawQuerySet, self).__init__(*args, **kw)
        self.timeout = timeout

    def __iter__(self):
        iterator = super(CachingRawQuerySet, self).__iter__
        if self.timeout == NO_CACHE:
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


def cached(model, function, key_, duration=DEFAULT_TIMEOUT):
    """Only calls the function if ``key`` is not already in the cache."""
    key = _function_cache_key(key_)
    val = cache_get(model, key)
    if val is None:
        log.debug('cache miss for %s' % key)
        val = function()
        cache_set(model, key, val, timeout=duration)
    else:
        log.debug('cache hit for %s' % key)
    return val


def cached_with(model, obj, f, f_key, timeout=DEFAULT_TIMEOUT):
    """Helper for caching a function call within an object's flush list."""

    try:
        obj_key = (obj.query_key() if hasattr(obj, 'query_key')
                   else obj.cache_key)
    except (AttributeError, EmptyResultSet):
        log.warning(u'%r cannot be cached.' % encoding.smart_str(obj))
        return f()

    key = '%s:%s' % tuple(map(encoding.smart_str, (f_key, obj_key)))
    return cached(model, f, key, timeout)
