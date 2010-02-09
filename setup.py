from setuptools import setup

import caching


setup(
    name='django-cache-machine',
    version=caching.__version__,
    description='Automatic caching and invalidation for Django models '
                'through the ORM.',
    long_description=open('README.rst').read(),
    author='Jeff Balogh',
    author_email='jbalogh@mozilla.com',
    url='http://github.com/jbalogh/django-cache-machine',
    license='BSD',
    packages=['caching', 'caching.backends'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        # I don't know what exactly this means, but why not?
        'Environment :: Web Environment :: Mozilla',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
