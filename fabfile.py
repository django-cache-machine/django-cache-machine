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

os.environ['DJANGO_SETTINGS_MODULE'] = 'cache-machine.settings'
os.environ['PYTHONPATH'] = os.pathsep.join([ROOT,
                                            os.path.join(ROOT, 'examples')])

env.hosts = ['jbalogh.me']

local = functools.partial(local, capture=False)


def doc(kind='html'):
    with cd('docs'):
        local('make clean %s' % kind)


def test():
    local('django-admin.py test -s')


def updoc():
    doc('dirhtml')
    rsync_project('p/%s' % NAME, 'docs/_build/dirhtml/', delete=True)
