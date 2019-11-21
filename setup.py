#!/usr/bin/env python
from setuptools import setup, find_packages
import re
import os
from codecs import open


name = "pout"

kwargs = {"name": name}

def read(path):
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return ""


vpath = os.path.join(name, "__init__.py")
if os.path.isfile(vpath):
    kwargs["packages"] = find_packages(exclude=["tests", "tests.*", "*_test*", "examples"])
else:
    vpath = "{}.py".format(name)
    kwargs["py_modules"] = [name]
kwargs["version"] = re.search(r"^__version__\s*=\s*[\'\"]([^\'\"]+)", read(vpath), flags=re.I | re.M).group(1)


# https://pypi.org/help/#description-content-type
kwargs["long_description"] = read('README.md')
kwargs["long_description_content_type"] = "text/markdown"

kwargs["tests_require"] = ["testdata"]
kwargs["install_requires"] = []


setup(
    description='Prints out python variables in an easy to read way, handy for debugging',
    author='Jay Marcyes',
    author_email='jay@marcyes.com',
    url='http://github.com/Jaymon/{}'.format(name),
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
    #test_suite = "pout_test",
    entry_points = {
        'console_scripts': [
#             '{}.json = {}.__main__:main_json'.format(name, name),
#             '{}.char = {}.__main__:main_char'.format(name, name)
#             '{}.inject = {}.__main__:main_inject'.format(name, name)
            '{} = {}.__main__:main'.format(name, name)
        ],
    },
    **kwargs
)
