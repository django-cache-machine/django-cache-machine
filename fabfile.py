"""
Creating standalone Django apps is a PITA because you're not in a project, so
you don't have a settings.py file.  I can never remember to define
DJANGO_SETTINGS_MODULE, so I run these commands which get the right env
automatically.
"""
import functools
import os

from fabric.api import local, cd, env
from fabric.contrib.project import rsync_project

NAME = os.path.basename(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.dirname(__file__))

os.environ['PYTHONPATH'] = os.pathsep.join([ROOT,
                                            os.path.join(ROOT, 'examples')])

env.hosts = ['jbalogh.me']

local = functools.partial(local, capture=False)


def doc(kind='html'):
    with cd('docs'):
        local('make clean %s' % kind)


SETTINGS = ('locmem_settings',
            'settings',
            'memcache_byid',
            'custom_backend')

try:
    import redis
    redis.Redis(host='localhost', port=6379).info()
    SETTINGS += ('redis_settings', 'redis_byid')
except Exception:
    print 'WARNING: Skipping redis tests.'

def test():
    for settings in SETTINGS:
        print settings
        os.environ['DJANGO_SETTINGS_MODULE'] = 'cache_machine.%s' % settings
        local('django-admin.py test')


def updoc():
    doc('dirhtml')
    rsync_project('p/%s' % NAME, 'docs/_build/dirhtml/', delete=True)
