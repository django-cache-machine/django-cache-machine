from setuptools import setup

import caching

setup(
    name="django-cache-machine",
    version=caching.__version__,
    description="Automatic caching and invalidation for Django models "
    "through the ORM.",
    long_description=open("README.rst").read(),
    author="Jeff Balogh",
    author_email="jbalogh@mozilla.com",
    url="http://github.com/django-cache-machine/django-cache-machine",
    license="BSD",
    packages=["caching"],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        # I don't know what exactly this means, but why not?
        "Environment :: Web Environment :: Mozilla",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
