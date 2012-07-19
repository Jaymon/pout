#!/usr/bin/env python
# I shamefully ripped most of this off from fbconsole because it was a setup.py I had
# readily available.
# http://docs.python.org/distutils/setupscript.html

import sys
from setuptools import setup

install_requires = []
extra = {}
version = '0.1.9'


setup(
    name='pout',
    version=version,
    description='Prints out python variables in an easy to read way, handy for debugging',
    author='Jay Marcyes',
    author_email='jay@marcyes.com',
    url='http://github.com/Jaymon/pout',
    package_dir={'': 'src'},
    py_modules=[
        'pout',
    ],
    license="MIT",
    install_requires=install_requires,
    zip_safe=True,
    classifiers=[
        'Development Status :: {}'.format(version),
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: MIT',
        'Operating System :: OS Independent',
        'Topic :: Debug',
        ],
    test_suite = "fbconsole.test_pout",
    entry_points = "", # http://stackoverflow.com/questions/774824/explain-python-entry-points
    **extra
)
