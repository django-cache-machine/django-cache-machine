"""
Creating standalone Django apps is a PITA because you're not in a project, so
you don't have a settings.py file.  I can never remember to define
DJANGO_SETTINGS_MODULE, so I run these commands which get the right env
automatically.
"""
import os
import sys
import argparse

from subprocess import call
try:
    from subprocess import check_output
except ImportError:
    # Python 2.6 doesn't have check_output. Note this will not raise a CalledProcessError
    # like check_output does, but it should work for our purposes.
    import subprocess
    check_output = lambda x: subprocess.Popen(x, stdout=subprocess.PIPE).communicate()[0]

NAME = os.path.basename(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.dirname(__file__))

os.environ['PYTHONPATH'] = os.pathsep.join([ROOT,
                                            os.path.join(ROOT, 'examples')])

SETTINGS = (
    'locmem_settings',
    'settings',
    'memcache_byid',
    'custom_backend',
    'redis_settings',
    'redis_byid',
)


def main():
    parser = argparse.ArgumentParser(description='Run the tests for django-cache-machine. '
                                     'If no options are specified, tests will be run with '
                                     'all settings files and without coverage.py.')
    parser.add_argument('--with-coverage', action='store_true',
                        help='Run tests with coverage.py and display coverage report')
    parser.add_argument('--settings', choices=SETTINGS,
                        help='Run tests only for the specified settings file')
    args = parser.parse_args()
    settings = args.settings and [args.settings] or SETTINGS
    results = []
    django_admin = check_output(['which', 'django-admin.py']).strip()
    for i, settings_module in enumerate(settings):
        print('Running tests for: %s' % settings_module)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'cache_machine.%s' % settings_module
        # append to the existing coverage data for all but the first run
        if args.with_coverage and i > 0:
            test_cmd = ['coverage', 'run', '--append']
        elif args.with_coverage:
            test_cmd = ['coverage', 'run']
        else:
            test_cmd = []
        test_cmd += [django_admin, 'test']
        results.append(call(test_cmd))
        if args.with_coverage:
            results.append(call(['coverage', 'report', '-m', '--fail-under', '70']))
    sys.exit(any(results) and 1 or 0)


if __name__ == "__main__":
    main()
