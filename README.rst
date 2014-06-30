=============
Cache Machine
=============

Cache Machine provides automatic caching and invalidation for Django models
through the ORM.

For full docs, see https://cache-machine.readthedocs.org/en/latest/.

.. image:: https://travis-ci.org/jbalogh/django-cache-machine.png
  :target: https://travis-ci.org/jbalogh/django-cache-machine


Requirements
------------

Cache Machine requires Django 1.3+.  It was written and tested on Python 2.6.


Installation
------------


Get it from `pypi <http://pypi.python.org/pypi/django-cache-machine>`_::

    pip install django-cache-machine

or `github <http://github.com/jbalogh/django-cache-machine>`_::

    pip install git+git://github.com/jbalogh/django-cache-machine.git#egg=django-cache-machine


Running Tests
-------------


Get it from `github <http://github.com/jbalogh/django-cache-machine>`_::

    git clone git://github.com/jbalogh/django-cache-machine.git
    cd django-cache-machine
    pip install -r requirements.txt
    fab test
