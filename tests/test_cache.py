from __future__ import unicode_literals

import django
import jinja2
import pickle
import logging

from django.conf import settings
from django.test import TestCase, TransactionTestCase
from django.utils import translation, encoding, six

if six.PY3:
    from unittest import mock
else:
    import mock
from nose.tools import eq_
from nose.plugins.skip import SkipTest

from caching import base, invalidation, config, compat
from .testapp.models import Addon, User

cache = invalidation.cache
log = logging.getLogger(__name__)

if django.get_version().startswith('1.3'):
    class settings_patch(object):
        def __init__(self, **kwargs):
            self.options = kwargs

        def __enter__(self):
            self._old_settings = dict((k, getattr(settings, k, None)) for k in self.options)
            for k, v in list(self.options.items()):
                setattr(settings, k, v)

        def __exit__(self, *args):
            for k in self.options:
                setattr(settings, k, self._old_settings[k])

    TestCase.settings = settings_patch


class CachingTestCase(TestCase):
    fixtures = ['tests/testapp/fixtures/testapp/test_cache.json']
    extra_apps = ['tests.testapp']

    def setUp(self):
        cache.clear()
        self.old_timeout = config.TIMEOUT
        if getattr(settings, 'CACHE_MACHINE_USE_REDIS', False):
            invalidation.redis.flushall()

    def tearDown(self):
        config.TIMEOUT = self.old_timeout

    def test_flush_key(self):
        """flush_key should work for objects or strings."""
        a = Addon.objects.get(id=1)
        eq_(base.flush_key(a.get_cache_key(incl_db=False)), base.flush_key(a))

    def test_cache_key(self):
        a = Addon.objects.get(id=1)
        eq_(a.cache_key, 'o:testapp.addon:1:default')

        keys = set((a.cache_key, a.author1.cache_key, a.author2.cache_key))
        eq_(set(a._cache_keys()), keys)

    def test_cache(self):
        """Basic cache test: second get comes from cache."""
        assert Addon.objects.get(id=1).from_cache is False
        assert Addon.objects.get(id=1).from_cache is True

    def test_filter_cache(self):
        assert Addon.objects.filter(id=1)[0].from_cache is False
        assert Addon.objects.filter(id=1)[0].from_cache is True

    def test_slice_cache(self):
        assert Addon.objects.filter(id=1)[:1][0].from_cache is False
        assert Addon.objects.filter(id=1)[:1][0].from_cache is True

    def test_invalidation(self):
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

        a.save()
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

    def test_invalidation_cross_locale(self):
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

        # Do query & invalidation in a different locale.
        old_locale = translation.get_language()
        translation.activate('fr')
        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

        a.save()

        translation.activate(old_locale)
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

    def test_fk_invalidation(self):
        """When an object is invalidated, its foreign keys get invalidated."""
        a = Addon.objects.get(id=1)
        assert User.objects.get(name='clouseroo').from_cache is False
        a.save()

        assert User.objects.get(name='clouseroo').from_cache is False

    def test_fk_parent_invalidation(self):
        """When a foreign key changes, any parent objects get invalidated."""
        assert Addon.objects.get(id=1).from_cache is False
        a = Addon.objects.get(id=1)
        assert a.from_cache is True

        u = User.objects.get(id=a.author1.id)
        assert u.from_cache is True
        u.name = 'fffuuu'
        u.save()

        assert User.objects.get(id=a.author1.id).from_cache is False
        a = Addon.objects.get(id=1)
        assert a.from_cache is False
        eq_(a.author1.name, 'fffuuu')

    def test_raw_cache(self):
        sql = 'SELECT * FROM %s WHERE id = 1' % Addon._meta.db_table
        raw = list(Addon.objects.raw(sql))
        eq_(len(raw), 1)
        raw_addon = raw[0]
        a = Addon.objects.get(id=1)
        for field in Addon._meta.fields:
            eq_(getattr(a, field.name), getattr(raw_addon, field.name))
        assert raw_addon.from_cache is False

        cached = list(Addon.objects.raw(sql))
        eq_(len(cached), 1)
        cached_addon = cached[0]
        a = Addon.objects.get(id=1)
        for field in Addon._meta.fields:
            eq_(getattr(a, field.name), getattr(cached_addon, field.name))
        assert cached_addon.from_cache is True

    def test_raw_cache_params(self):
        """Make sure the query params are included in the cache key."""
        sql = 'SELECT * from %s WHERE id = %%s' % Addon._meta.db_table
        raw = list(Addon.objects.raw(sql, [1]))[0]
        eq_(raw.id, 1)

        raw2 = list(Addon.objects.raw(sql, [2]))[0]
        eq_(raw2.id, 2)

    @mock.patch('caching.base.CacheMachine')
    def test_raw_nocache(self, CacheMachine):
        base.TIMEOUT = 60
        sql = 'SELECT * FROM %s WHERE id = 1' % Addon._meta.db_table
        raw = list(Addon.objects.raw(sql, timeout=config.NO_CACHE))
        eq_(len(raw), 1)
        raw_addon = raw[0]
        assert not hasattr(raw_addon, 'from_cache')
        assert not CacheMachine.called

    @mock.patch('caching.base.cache')
    def test_count_cache(self, cache_mock):
        config.TIMEOUT = 60
        cache_mock.scheme = 'memcached'
        cache_mock.get.return_value = None

        q = Addon.objects.all()
        q.count()

        assert cache_mock.set.call_args, 'set not called'
        args, kwargs = cache_mock.set.call_args
        key, value, timeout = args
        eq_(value, 2)
        eq_(timeout, 60)

    @mock.patch('caching.base.cached')
    def test_count_none_timeout(self, cached_mock):
        config.TIMEOUT = config.NO_CACHE
        Addon.objects.count()
        eq_(cached_mock.call_count, 0)

    @mock.patch('caching.base.cached')
    def test_count_nocache(self, cached_mock):
        base.TIMEOUT = 60
        Addon.objects.no_cache().count()
        eq_(cached_mock.call_count, 0)

    def test_queryset_flush_list(self):
        """Check that we're making a flush list for the queryset."""
        q = Addon.objects.all()
        objects = list(q)  # Evaluate the queryset so it gets cached.
        base.invalidator.add_to_flush_list({q.flush_key(): ['remove-me']})
        cache.set('remove-me', 15)

        Addon.objects.invalidate(objects[0])
        assert cache.get(q.flush_key()) is None
        assert cache.get('remove-me') is None

    def test_jinja_cache_tag_queryset(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])

        def check(q, expected):
            t = env.from_string(
                "{% cache q %}{% for x in q %}{{ x.id }}:{{ x.val }};"
                "{% endfor %}{% endcache %}")
            eq_(t.render(q=q), expected)

        # Get the template in cache, then hijack iterator to make sure we're
        # hitting the cached fragment.
        check(Addon.objects.all(), '1:42;2:42;')
        qs = Addon.objects.all()
        qs.iterator = mock.Mock()
        check(qs, '1:42;2:42;')
        assert not qs.iterator.called

        # Make changes, make sure we dropped the cached fragment.
        a = Addon.objects.get(id=1)
        a.val = 17
        a.save()

        q = Addon.objects.all()
        cache.get(q.flush_key())
        assert cache.get(q.flush_key()) is None

        check(Addon.objects.all(), '1:17;2:42;')
        qs = Addon.objects.all()
        qs.iterator = mock.Mock()
        check(qs, '1:17;2:42;')

    def test_jinja_cache_tag_object(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        addon = Addon.objects.get(id=1)

        def check(obj, expected):
            t = env.from_string(
                '{% cache obj, 30 %}{{ obj.id }}:{{ obj.val }}{% endcache %}')
            eq_(t.render(obj=obj), expected)

        check(addon, '1:42')
        addon.val = 17
        addon.save()
        check(addon, '1:17')

    def test_jinja_multiple_tags(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        addon = Addon.objects.get(id=1)
        template = ("{% cache obj %}{{ obj.id }}{% endcache %}\n"
                    "{% cache obj %}{{ obj.val }}{% endcache %}")

        def check(obj, expected):
            t = env.from_string(template)
            eq_(t.render(obj=obj), expected)

        check(addon, '1\n42')
        addon.val = 17
        addon.save()
        check(addon, '1\n17')

    def test_jinja_cache_tag_extra(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        addon = Addon.objects.get(id=1)

        template = ('{% cache obj, extra=[obj.key] %}{{ obj.id }}:'
                    '{{ obj.key }}{% endcache %}')

        def check(obj, expected):
            t = env.from_string(template)
            eq_(t.render(obj=obj), expected)

        addon.key = 1
        check(addon, '1:1')
        addon.key = 2
        check(addon, '1:2')

        template = ('{% cache obj, 10, extra=[obj.key] %}{{ obj.id }}:'
                    '{{ obj.key }}{% endcache %}')
        addon.key = 1
        check(addon, '1:1')
        addon.key = 2
        check(addon, '1:2')

    def test_cached_with(self):
        counter = mock.Mock()

        def expensive():
            counter()
            return counter.call_count

        a = Addon.objects.get(id=1)
        f = lambda: base.cached_with(a, expensive, 'key')

        # Only gets called once.
        eq_(f(), 1)
        eq_(f(), 1)

        # Switching locales does not reuse the cache.
        old_locale = translation.get_language()
        translation.activate('fr')
        eq_(f(), 2)

        # Called again after flush.
        a.save()
        eq_(f(), 3)

        translation.activate(old_locale)
        eq_(f(), 4)

        counter.reset_mock()
        q = Addon.objects.filter(id=1)
        f = lambda: base.cached_with(q, expensive, 'key')

        # Only gets called once.
        eq_(f(), 1)
        eq_(f(), 1)

        # Called again after flush.
        list(q)[0].save()
        eq_(f(), 2)
        eq_(f(), 2)

    def test_cached_with_bad_object(self):
        """cached_with shouldn't fail if the object is missing a cache key."""
        counter = mock.Mock()

        def f():
            counter()
            return counter.call_count

        eq_(base.cached_with([], f, 'key'), 1)

    def test_cached_with_unicode(self):
        u = encoding.smart_bytes('\\u05ea\\u05d9\\u05d0\\u05d5\\u05e8 '
                                 '\\u05d0\\u05d5\\u05e1\\u05e3')
        obj = mock.Mock()
        obj.query_key.return_value = 'xxx'
        obj.flush_key.return_value = 'key'
        f = lambda: 1
        eq_(base.cached_with(obj, f, 'adf:%s' % u), 1)

    def test_cached_method(self):
        a = Addon.objects.get(id=1)
        eq_(a.calls(), (1, 1))
        eq_(a.calls(), (1, 1))

        a.save()
        # Still returns 1 since the object has it's own local cache.
        eq_(a.calls(), (1, 1))
        eq_(a.calls(3), (3, 2))

        a = Addon.objects.get(id=1)
        eq_(a.calls(), (1, 3))
        eq_(a.calls(4), (4, 4))
        eq_(a.calls(3), (3, 2))

        b = Addon.objects.create(id=5, val=32, author1_id=1, author2_id=2)
        eq_(b.calls(), (1, 5))

        # Make sure we're updating the wrapper's docstring.
        eq_(b.calls.__doc__, Addon.calls.__doc__)

    @mock.patch('caching.base.CacheMachine')
    def test_no_cache_from_manager(self, CacheMachine):
        a = Addon.objects.no_cache().get(id=1)
        eq_(a.id, 1)
        assert not hasattr(a, 'from_cache')
        assert not CacheMachine.called

    @mock.patch('caching.base.CacheMachine')
    def test_no_cache_from_queryset(self, CacheMachine):
        a = Addon.objects.all().no_cache().get(id=1)
        eq_(a.id, 1)
        assert not hasattr(a, 'from_cache')
        assert not CacheMachine.called

    def test_timeout_from_manager(self):
        q = Addon.objects.cache(12).filter(id=1)
        eq_(q.timeout, 12)
        a = q.get()
        assert hasattr(a, 'from_cache')
        eq_(a.id, 1)

    def test_timeout_from_queryset(self):
        q = Addon.objects.all().cache(12).filter(id=1)
        eq_(q.timeout, 12)
        a = q.get()
        assert hasattr(a, 'from_cache')
        eq_(a.id, 1)

    @mock.patch('memcache.Client.set')
    def test_infinite_timeout(self, mock_set):
        """
        Test that memcached infinite timeouts work with all Django versions.
        """
        if not any(['memcache' in c['BACKEND'] for c in settings.CACHES.values()]):
            raise SkipTest('This test requires that Django use memcache')
        cache.set('foo', 'bar', timeout=compat.FOREVER)
        # for memcached, 0 timeout means store forever
        mock_set.assert_called_with(':1:foo', 'bar', 0)

    def test_cache_and_no_cache(self):
        """Whatever happens last sticks."""
        q = Addon.objects.no_cache().cache(12).filter(id=1)
        eq_(q.timeout, 12)

        no_cache = q.no_cache()

        # The querysets don't share anything.
        eq_(q.timeout, 12)
        assert no_cache.timeout != 12

        assert not hasattr(no_cache.get(), 'from_cache')

        eq_(q.get().id, 1)
        assert hasattr(q.get(), 'from_cache')

    @mock.patch('caching.base.cache')
    def test_cache_machine_timeout(self, cache):
        cache.scheme = 'memcached'
        cache.get.return_value = None
        cache.get_many.return_value = {}

        a = Addon.objects.cache(12).get(id=1)
        eq_(a.id, 1)

        assert cache.add.called
        args, kwargs = cache.add.call_args
        eq_(kwargs, {'timeout': 12})

    def test_unicode_key(self):
        list(User.objects.filter(name='\\xfcmla\\xfct'))

    def test_empty_in(self):
        # Raised an exception before fixing #2.
        eq_([], list(User.objects.filter(pk__in=[])))

    def test_empty_in_count(self):
        # Regression test for #14.
        eq_(0, User.objects.filter(pk__in=[]).count())

    def test_empty_queryset(self):
        for k in (1, 1):
            with self.assertNumQueries(k):
                eq_(len(Addon.objects.filter(pk=42)), 0)

    @mock.patch('caching.config.CACHE_EMPTY_QUERYSETS', True)
    def test_cache_empty_queryset(self):
        for k in (1, 0):
            with self.assertNumQueries(k):
                eq_(len(Addon.objects.filter(pk=42)), 0)

    def test_invalidate_empty_queryset(self):
        u = User.objects.create()
        eq_(list(u.addon_set.all()), [])
        Addon.objects.create(val=42, author1=u, author2=u)
        eq_([a.val for a in u.addon_set.all()], [42])

    def test_invalidate_new_related_object(self):
        u = User.objects.create()
        Addon.objects.create(val=42, author1=u, author2=u)
        eq_([a.val for a in u.addon_set.all()], [42])
        Addon.objects.create(val=17, author1=u, author2=u)
        eq_([a.val for a in u.addon_set.all()], [42, 17])

    def test_make_key_unicode(self):
        translation.activate('en-US')
        f = 'fragment\xe9\x9b\xbb\xe8\x85\xa6\xe7\x8e'
        # This would crash with a unicode error.
        base.make_key(f, with_locale=True)
        translation.deactivate()

    @mock.patch('caching.invalidation.cache.get_many')
    def test_get_flush_lists_none(self, cache_mock):
        if not getattr(settings, 'CACHE_MACHINE_USE_REDIS', False):
            cache_mock.return_value.values.return_value = [None, [1]]
            eq_(base.invalidator.get_flush_lists(None), set([1]))

    def test_parse_backend_uri(self):
        """ Test that parse_backend_uri works as intended. Regression for #92. """
        from caching.invalidation import parse_backend_uri
        uri = 'redis://127.0.0.1:6379?socket_timeout=5'
        host, params = parse_backend_uri(uri)
        self.assertEqual(host, '127.0.0.1:6379')
        self.assertEqual(params, {'socket_timeout': '5'})

    @mock.patch('caching.config.CACHE_INVALIDATE_ON_CREATE', 'whole-model')
    def test_invalidate_on_create_enabled(self):
        """ Test that creating new objects invalidates cached queries for that model. """
        eq_([a.name for a in User.objects.all()], ['fliggy', 'clouseroo'])
        User.objects.create(name='spam')
        users = User.objects.all()
        # our new user should show up and the query should not have come from the cache
        eq_([a.name for a in users], ['fliggy', 'clouseroo', 'spam'])
        assert not any([u.from_cache for u in users])
        # if we run it again, it should be cached this time
        users = User.objects.all()
        eq_([a.name for a in users], ['fliggy', 'clouseroo', 'spam'])
        assert all([u.from_cache for u in User.objects.all()])

    @mock.patch('caching.config.CACHE_INVALIDATE_ON_CREATE', None)
    def test_invalidate_on_create_disabled(self):
        """
        Test that creating new objects does NOT invalidate cached queries when
        whole-model invalidation on create is disabled.
        """
        users = User.objects.all()
        assert users, "Can't run this test without some users"
        assert not any([u.from_cache for u in users])
        User.objects.create(name='spam')
        assert all([u.from_cache for u in User.objects.all()])

    def test_pickle_queryset(self):
        """
        Test for CacheingQuerySet.__getstate__ and CachingQuerySet.__setstate__.
        """
        # Make sure CachingQuerySet.timeout, when set to DEFAULT_TIMEOUT, can be safely
        # pickled/unpickled on/from different Python processes which may have different
        # underlying values for DEFAULT_TIMEOUT:
        q1 = Addon.objects.all()
        assert q1.timeout == compat.DEFAULT_TIMEOUT
        pickled = pickle.dumps(q1)
        new_timeout = object()
        with mock.patch('caching.base.DEFAULT_TIMEOUT', new_timeout):
            q2 = pickle.loads(pickled)
            assert q2.timeout == new_timeout
        # Make sure values other than DEFAULT_TIMEOUT remain unaffected:
        q1 = Addon.objects.cache(10).all()
        assert q1.timeout == 10
        pickled = pickle.dumps(q1)
        with mock.patch('caching.base.DEFAULT_TIMEOUT', new_timeout):
            q2 = pickle.loads(pickled)
            assert q2.timeout == 10


# use TransactionTestCase so that ['TEST']['MIRROR'] setting works
# see https://code.djangoproject.com/ticket/23718
class MultiDbTestCase(TransactionTestCase):
    multi_db = True
    fixtures = ['tests/testapp/fixtures/testapp/test_cache.json']
    extra_apps = ['tests.testapp']

    def test_multidb_cache(self):
        """ Test where master and slave DB result in two different cache keys """
        assert Addon.objects.get(id=1).from_cache is False
        assert Addon.objects.get(id=1).from_cache is True

        from_slave = Addon.objects.using('slave').get(id=1)
        assert from_slave.from_cache is False
        assert from_slave._state.db == 'slave'

    def test_multidb_fetch_by_id(self):
        """ Test where master and slave DB result in two different cache keys with FETCH_BY_ID"""
        with self.settings(FETCH_BY_ID=True):
            assert Addon.objects.get(id=1).from_cache is False
            assert Addon.objects.get(id=1).from_cache is True

            from_slave = Addon.objects.using('slave').get(id=1)
            assert from_slave.from_cache is False
            assert from_slave._state.db == 'slave'

    def test_multidb_master_slave_invalidation(self):
        """ Test saving an object on one DB invalidates it for all DBs """
        log.debug('priming the DB & cache')
        master_obj = User.objects.using('default').create(name='new-test-user')
        slave_obj = User.objects.using('slave').get(name='new-test-user')
        assert slave_obj.from_cache is False
        log.debug('deleting the original object')
        User.objects.using('default').filter(pk=slave_obj.pk).delete()
        log.debug('re-creating record with a new primary key')
        master_obj = User.objects.using('default').create(name='new-test-user')
        log.debug('attempting to force re-fetch from DB (should not use cache)')
        slave_obj = User.objects.using('slave').get(name='new-test-user')
        assert slave_obj.from_cache is False
        eq_(slave_obj.pk, master_obj.pk)

    def test_multidb_no_db_crossover(self):
        """ Test no crossover of objects with identical PKs """
        master_obj = User.objects.using('default').create(name='new-test-user')
        master_obj2 = User.objects.using('master2').create(pk=master_obj.pk, name='other-test-user')
        # prime the cache for the default DB
        master_obj = User.objects.using('default').get(name='new-test-user')
        assert master_obj.from_cache is False
        master_obj = User.objects.using('default').get(name='new-test-user')
        assert master_obj.from_cache is True
        # prime the cache for the 2nd master DB
        master_obj2 = User.objects.using('master2').get(name='other-test-user')
        assert master_obj2.from_cache is False
        master_obj2 = User.objects.using('master2').get(name='other-test-user')
        assert master_obj2.from_cache is True
        # ensure no crossover between databases
        assert master_obj.name != master_obj2.name
