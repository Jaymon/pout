#!/usr/bin/env python
# http://docs.python.org/distutils/setupscript.html
# http://docs.python.org/2/distutils/examples.html

from setuptools import setup, find_packages
import re
import os
from codecs import open


name = "pout"

def read(path):
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return ""

path = os.path.join(name, "__init__.py")
version = re.search("^__version__\s*=\s*[\'\"]([^\'\"]+)", read(path), flags=re.I | re.M).group(1)

long_description = read('README.rst')

setup(
    name=name,
    version=version,
    description='Prints out python variables in an easy to read way, handy for debugging',
    long_description=long_description,
    author='Jay Marcyes',
    author_email='jay@marcyes.com',
    url='http://github.com/Jaymon/{}'.format(name),
    #py_modules=[name],
    packages=find_packages(),
    license="MIT",
    classifiers=[ # https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    tests_require=['testdata'],
    #test_suite = "pout_test",
    entry_points = {
        'console_scripts': [
#             '{}.json = {}.__main__:main_json'.format(name, name),
#             '{}.char = {}.__main__:main_char'.format(name, name)
#             '{}.inject = {}.__main__:main_inject'.format(name, name)
            '{} = {}.__main__:main'.format(name, name)
        ],
    }
)
