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


Running Tests
-------------

Get it from `github <http://github.com/django-cache-machine/django-cache-machine>`_::

    git clone git://github.com/django-cache-machine/django-cache-machine.git
    cd django-cache-machine
    pip install -r requirements/py3.txt  # or py2.txt for Python 2
    python run_tests.py
