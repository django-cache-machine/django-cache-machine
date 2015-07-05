from django.conf import settings

NO_CACHE = -1
WHOLE_MODEL = 'whole-model'

CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', '')
FETCH_BY_ID = getattr(settings, 'FETCH_BY_ID', False)
FLUSH = CACHE_PREFIX + ':flush:'
CACHE_EMPTY_QUERYSETS = getattr(settings, 'CACHE_EMPTY_QUERYSETS', False)
TIMEOUT = getattr(settings, 'CACHE_COUNT_TIMEOUT', NO_CACHE)
CACHE_INVALIDATE_ON_CREATE = getattr(settings, 'CACHE_INVALIDATE_ON_CREATE', None)
CACHE_MACHINE_NO_INVALIDATION = getattr(settings, 'CACHE_MACHINE_NO_INVALIDATION', False)
CACHE_MACHINE_USE_REDIS = getattr(settings, 'CACHE_MACHINE_USE_REDIS', False)

_invalidate_on_create_values = (None, WHOLE_MODEL)
if CACHE_INVALIDATE_ON_CREATE not in _invalidate_on_create_values:
    raise ValueError('CACHE_INVALIDATE_ON_CREATE must be one of: '
                     '%s' % _invalidate_on_create_values)
