import django
from django.db import models

from unittest import mock

from caching.base import CachingMixin, CachingManager, cached_method
# This global call counter will be shared among all instances of an Addon.
call_counter = mock.Mock()


class User(CachingMixin, models.Model):
    name = models.CharField(max_length=30)

    objects = CachingManager()

    if django.VERSION[0] >= 2:
        class Meta:
            # Tell Django to use this manager when resolving foreign keys. (Django >= 2.0)
            base_manager_name = 'objects'


class Addon(CachingMixin, models.Model):
    val = models.IntegerField()
    author1 = models.ForeignKey(User, on_delete=models.CASCADE)
    author2 = models.ForeignKey(User, related_name='author2_set', on_delete=models.CASCADE)

    objects = CachingManager()

    class Meta:
        # without this, Postgres & SQLite return objects in different orders:
        ordering = ('pk',)

    @cached_method
    def calls(self, arg=1):
        """This is a docstring for calls()"""
        call_counter()
        return arg, call_counter.call_count
