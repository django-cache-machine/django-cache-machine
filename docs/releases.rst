.. _release-notes:

Release Notes
==================

v0.9 (release date TBD)
-----------------------

- Support for Python 3

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
