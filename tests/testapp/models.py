from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

import mock

from caching.base import CachingMixin, CachingManager, cached_method


# This global call counter will be shared among all instances of an Addon.
call_counter = mock.Mock()


class User(CachingMixin, models.Model):
    name = models.CharField(max_length=30)

    objects = CachingManager()


class Addon(CachingMixin, models.Model):
    val = models.IntegerField()
    author1 = models.ForeignKey(User)
    author2 = models.ForeignKey(User, related_name='author2_set')

    objects = CachingManager()

    @cached_method
    def calls(self, arg=1):
        """This is a docstring for calls()"""
        call_counter()
        return arg, call_counter.call_count


class Comment(CachingMixin, models.Model):
    object_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    object = generic.GenericForeignKey('object_type', 'object_id')

    object2_type = models.ForeignKey(ContentType, null=True, related_name='+')
    object2_id = models.PositiveIntegerField(null=True)
    object2 = generic.GenericForeignKey('object2_type', 'object2_id')

    objects = CachingManager()
