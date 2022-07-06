=============
Cache Machine
=============

Cache Machine provides automatic caching and invalidation for Django models
through the ORM.

For full docs, see https://cache-machine.readthedocs.org/en/latest/.

.. image:: https://github.com/django-cache-machine/django-cache-machine/actions/workflows/ci.yaml/badge.svg
  :target: https://github.com/django-cache-machine/django-cache-machine/actions/workflows/ci.yaml


Requirements
------------

Cache Machine currently works with:

* Django 2.2, 3.0, 3.1, 3.2, and 4.0
* Python 3.6, 3.7, 3.8, 3.9, and 3.10

The last version to support Python 2.7 and Django 1.11 is ``django-cache-machine==1.1.0``.

Installation
------------

Get it from `pypi <http://pypi.python.org/pypi/django-cache-machine>`_::

    pip install django-cache-machine


Running Tests
-------------

Get it from `github <http://github.com/django-cache-machine/django-cache-machine>`_::

    git clone git://github.com/django-cache-machine/django-cache-machine.git
    cd django-cache-machine
    pip install -r dev-requirements.txt
    python run_tests.py
