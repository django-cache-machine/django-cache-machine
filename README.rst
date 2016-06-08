=============
Cache Machine
=============

Cache Machine provides automatic caching and invalidation for Django models
through the ORM.

For full docs, see https://cache-machine.readthedocs.org/en/latest/.

.. image:: https://travis-ci.org/django-cache-machine/django-cache-machine.svg?branch=master
  :target: https://travis-ci.org/django-cache-machine/django-cache-machine

.. image:: https://coveralls.io/repos/django-cache-machine/django-cache-machine/badge.svg?branch=master
  :target: https://coveralls.io/r/django-cache-machine/django-cache-machine?branch=master


Requirements
------------

Cache Machine works with Django 1.4-1.8 and Python 2.6, 2.7, 3.3 and 3.4.


Installation
------------

Get it from `pypi <http://pypi.python.org/pypi/django-cache-machine>`_::

    pip install django-cache-machine

or `github <http://github.com/django-cache-machine/django-cache-machine>`_::

    pip install -e git://github.com/django-cache-machine/django-cache-machine.git#egg=django-cache-machine

then add ``caching`` to your ``INSTALLED_APPS``.


Configuration
-------------

To use Cache Machine with your own models, subclass from
``caching.base.CachingMixin`` and use or subclass
``caching.base.CachingManager`` for your manager instance.

To use Cache Machine with arbitrary models specify the import string with the
``CACHE_MACHINE_MODELS`` setting. This can also be used to register models
automatically generated from``ManyToManyField``s by specifying the ``through``
attribute on the ManyToManyField directly.

Example:
~~~~~~~~

``yourapp/models.py``:

    from django.db import models

    class Thing(models.Model):
        others = models.ManyToManyField('self')


``anotherapp/models.py``:

    from django.db import models

    class OtherThing(models.Model):
        # ...

        objects = models.Manager()


``settings.py``:

    CACHE_MACHINE_MODELS = {
        # Cache the automatically generated intermediate model for the ManyToManyField
        'yourapp.models.Thing.others.through': {},

        # Cache a model from another app
        'anotherapp.models.OtherThing': {
            # Options dictionary
        }
    }

Right now the only available option is ``manager_name``, which you can use to
cache only certain managers. This option defaults to ``objects``, so it can be
safely omitted in almost all cases.


Running Tests
-------------

Get it from `github <http://github.com/django-cache-machine/django-cache-machine>`_::

    git clone git://github.com/django-cache-machine/django-cache-machine.git
    cd django-cache-machine
    pip install -r requirements/py3.txt  # or py2.txt for Python 2
    python run_tests.py
