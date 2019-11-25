.. _caching:

=============
Cache Machine
=============

Cache Machine provides automatic caching and invalidation for Django models
through the ORM.  The code is hosted on
`github <http://github.com/django-cache-machine/django-cache-machine>`_.

For an overview of new features and backwards-incompatible changes which may
affect you, please see the :ref:`release-notes`.

Settings
--------

Older versions of Cache Machine required you to use customized cache backends. These are no longer
needed and they have been removed from Cache Machine. Use the standard Django cache backends.

COUNT queries
^^^^^^^^^^^^^

Calls to ``QuerySet.count()`` can be cached, but they cannot be reliably
invalidated.  Cache Machine would have to do a full select to figure out the
object keys, which is probably much more data than you want to pull.  I
recommend a short cache timeout; long enough to avoid repetitive queries, but
short enough that stale counts won't be a big deal.  ::

    CACHE_COUNT_TIMEOUT = 60  # seconds, not too long.

By default, calls to ``QuerySet.count()`` are not cached. They are only cached
if ``CACHE_COUNT_TIMEOUT`` is set to a value other than
``caching.base.NO_CACHE``.

Empty querysets
^^^^^^^^^^^^^^^

By default cache machine will not cache empty querysets. To cache them::

    CACHE_EMPTY_QUERYSETS = True

.. _object-creation:

Object creation
^^^^^^^^^^^^^^^

By default Cache Machine does not invalidate queries when a new object is
created, because it can be expensive to maintain a flush list of all the
queries associated with a given table and cause significant disruption on
high-volume sites when *all* the queries for a particular model are
invalidated at once. If these are not issues for your site and immediate
inclusion of created objects in previously cached queries is desired, you
can enable this feature as follows::

    CACHE_INVALIDATE_ON_CREATE = 'whole-model'

Cache Manager
-------------

To enable caching for a model, add the :class:`~caching.base.CachingManager` to
that class and inherit from the :class:`~caching.base.CachingMixin`.  If you
want related lookups (foreign keys) to hit the cache, ``CachingManager`` must
be the default manager.  If you have multiple managers that should be cached,
return a :class:`~caching.base.CachingQuerySet` from the other manager's
``get_queryset`` method instead of subclassing ``CachingManager``, since that
would hook up the post_save and post_delete signals multiple times.

Here's what a minimal cached model looks like::

    from django.db import models

    from caching.base import CachingManager, CachingMixin

    class Zomg(CachingMixin, models.Model):
        val = models.IntegerField()

        objects = CachingManager()

        # if you use Django 2.0 or later, you must set base_manager_name
        class Meta:
            base_manager_name = 'objects'  # Attribute name of CachingManager(), above

Whenever you run a query, ``CachingQuerySet`` will try to find that query in
the cache.  Queries are keyed by ``{prefix}:{sql}``. If it's there, we return
the cached result set and everyone is happy.  If the query isn't in the cache,
the normal codepath to run a database query is executed.  As the objects in the
result set are iterated over, they are added to a list that will get cached
once iteration is done.

.. note::
    Nothing will be cached if the QuerySet is not iterated through completely.

Caching is supported for normal :class:`QuerySets <django.db.models.QuerySet>` and
for :meth:`django.db.models.Manager.raw`.  At this time, caching has not been
implemented for ``QuerySet.values`` or ``QuerySet.values_list``.

To support easy cache invalidation, we use "flush lists" to mark the cached
queries an object belongs to.  That way, all queries where an object was found
will be invalidated when that object changes.  Flush lists map an object key to
a list of query keys.

When an object is saved or deleted, all query keys in its flush list will be
deleted.  In addition, the flush lists of its foreign key relations will be
cleared.  To avoid stale foreign key relations, any cached objects will be
flushed when the object their foreign key points to is invalidated.

During cache invalidation, we explicitly set a None value instead of just
deleting so we don't have any race condtions where:

 * Thread 1 -> Cache miss, get object from DB
 * Thread 2 -> Object saved, deleted from cache
 * Thread 1 -> Store (stale) object fetched from DB in cache

The foundations of this module were derived from `Mike Malone's`_
`django-caching`_.

.. _`Mike Malone's`: http://immike.net/
.. _django-caching: http://github.com/mmalone/django-caching/

Changing the timeout of a CachingQuerySet instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the timeout for a ``CachingQuerySet`` instance will be the timeout
of the underlying cache being used by Cache Machine. To change the timeout of
a ``CachingQuerySet`` instance, you can assign a different value to the
``timeout`` attribute which represents the number of seconds to cache for

For example::

    def get_objects(name):
        qs = CachedClass.objects.filter(name=name)
        qs.timeout = 5  # seconds
        return qs

To disable caching for a particular ``CachingQuerySet`` instance, set the
``timeout`` attribute to ``caching.base.NO_CACHE``.

Manual Caching
--------------

Some things can be cached better outside of the ORM, so Cache Machine provides
the function :func:`caching.base.cached` for caching arbitrary objects.  Using
this function gives you more control over what gets cached, and for how long,
while abstracting a few repetitive elements.

.. autofunction:: caching.base.cached


Template Caching
----------------

Cache Machine includes a Jinja2 extension to cache template fragments based on
a queryset or cache-aware object.  These fragments will get invalidated on
using the same rules as ``CachingQuerySets``.

First, add it to your template environment::

    env = jinja2.Environment(extensions=['caching.ext.cache'])

.. highlight:: jinja

Now wrap all your queryset looping with the ``cache`` tag. ::

    {% cache objects %}  {# objects is a CachingQuerySet #}
      {% for obj in objects %}
        ...
      {% endfor %}
    {% endcache %}

...and for caching by single objects::

    {% cache object %}
      ...expensive processing...
    {% endcache %}

The tag can take an optional timeout. ::

    {% cache objects, 500 %}

.. highlight:: python

If someone wants to write a template tag for Django templates, I'd love to add
it.


Redis Support
-------------

Cache Machine support storing flush lists in Redis rather than memcached, which
is more efficient because Redis can manipulate the lists on the server side
rather than having to transfer the entire list back and forth for each
modification.

To enable Redis support for Cache Machine, add the following to your settings
file, replacing ``localhost`` with the hostname of your Redis server::

    CACHE_MACHINE_USE_REDIS = True
    REDIS_BACKEND = 'redis://localhost:6379'

.. note::
    When using Redis, memcached is still used for caching model objects, i.e.,
    only the flush lists are stored in Redis. You still need to configure
    ``CACHES`` the way you would normally for Cache Machine.


Classes That May Interest You
-----------------------------

.. autoclass:: caching.base.CachingModelIterable

.. autoclass:: caching.base.CachingManager
    :members:

    This :class:`manager <django.db.models.Manager>` always returns a
    :class:`~caching.CachingQuerySet`, and hooks up ``post_save`` and
    ``post_delete`` signals to invalidate caches.

.. autoclass:: caching.base.CachingMixin
    :members:

.. class:: caching.base.CachingQuerySet

    Overrides the default :class:`~django.db.models.QuerySet` to fetch objects
    from cache before hitting the database.
