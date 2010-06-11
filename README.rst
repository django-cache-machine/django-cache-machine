=============
Cache Machine
=============

Cache Machine provides automatic caching and invalidation for Django models
through the ORM.

For full docs, see http://jbalogh.me/projects/cache-machine.


Requirements
------------

Cache Machine requires Django 1.2 (currently on trunk).  It was written and
tested on Python 2.6.


Installation
------------


Get it from `pypi <http://pypi.python.org/pypi/django-cache-machine>`_::

    pip install django-cache-machine

or `github <http://github.com/jbalogh/django-cache-machine>`_::

    pip install -e git://github.com/jbalogh/django-cache-machine.git#egg=django-cache-machine


Running Tests
-------------


Get it from `github <http://github.com/jbalogh/django-cache-machine>`_::

    git clone git://github.com/jbalogh/django-cache-machine.git
    cd django-cache-machine
    pip install -r requirements.txt
    fab test
