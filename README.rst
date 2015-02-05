=============
Cache Machine
=============

Cache Machine provides automatic caching and invalidation for Django models
through the ORM.

For full docs, see https://cache-machine.readthedocs.org/en/latest/.

.. image:: https://travis-ci.org/asketsus/django-cache-machine.png
  :target: https://travis-ci.org/asketsus/django-cache-machine

=============
Original Version
=============

This cache machine is a fork from https://github.com/jbalogh/django-cache-machine/. It has been reimplemented
to invalidate queryset after any change in his related model.

This solve a set of problems after do a POST/PUT operation, where Query sets were not invalidated although
they had new rows.

Requirements
------------

Cache Machine requires Django 1.3+.  It was written and tested on Python 2.7.


Installation
------------


Get it from `github <http://github.com/asketsus/django-cache-machine>`_::

    pip install -e git://github.com/asketsus/django-cache-machine.git#egg=django-cache-machine


Running Tests
-------------


Get it from `github <http://github.com/asketsus/django-cache-machine>`_::

    git clone git://github.com/asketsus/django-cache-machine.git
    cd django-cache-machine
    pip install -r requirements.txt
    fab test
