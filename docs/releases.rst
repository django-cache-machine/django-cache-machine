.. _release-notes:

Release Notes
==================

v0.9.1 (2015-10-22)
-----------------

- Fix bug that prevented objects retrieved via cache machine from being
  re-cached by application code (see PR #103)
- Fix bug that prevented caching objects forever when using Django <= 1.5
  (see PR #104)
- Fix regression (introduced in 0.8) that broke invalidation when an object
  was cached via a slave database and later modified or deleted via the
  master database, when using master/slave replication (see PR #105). Note
  this change may cause unexpected invalidation when sharding across DBs
  that share both a schema and primary key values or other attributes.

v0.9 (2015-07-29)
-----------------

- Support for Python 3
- A new setting, ``CACHE_INVALIDATE_ON_CREATE``, which facilitates invalidation
  when a new model object is created. For more information, see
  :ref:`object-creation`.

v0.8.1 (2015-07-03)
-----------------------

This release is primarily aimed at adding support for more recent versions of
Django and catching up on recent contributions.

- Support for Django 1.7 and Django 1.8
- Fix bug in parsing of ``REDIS_BACKEND`` URI
- Miscellaneous bug fixes and documentation corrections

Backwards Incompatible Changes
________________________________

- Dropped support for the old style ``caching.backends.memcached.CacheClass`` and
  ``caching.backends.locmem.CacheClass`` classes. Support for this naming
  has been deprecated since Django 1.3. You will need to switch your project
  to use ``MemcachedCache``, ``PyLibMCCache``, or ``LocMemCache`` in place of
  ``CacheClass``.
