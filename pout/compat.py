# -*- coding: utf-8 -*-

import sys

# ripped from https://github.com/kennethreitz/requests/blob/master/requests/compat.py
_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py2:
    basestring = basestring
    unicode = unicode
    range = xrange # range is now always an iterator

    from collections import Callable, Iterable, Set, KeysView
    import Queue as queue
    import thread as _thread
    import __builtin__ as builtins
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    import inspect
    inspect.getfullargspec = inspect.getargspec

    import tokenize
    # make the 2.7 and 3.7 tokenize apis similar
    # https://github.com/python/cpython/blob/3.7/Lib/tokenize.py
    # https://docs.python.org/3.7/library/tokenize.html
    # https://github.com/python/cpython/blob/2.7/Lib/tokenize.py
    # https://docs.python.org/2.7/library/tokenize.html
    def tokenizer(*args, **kwargs):
        import collections
        TokenInfo = collections.namedtuple('TokenInfo', 'type string start end line')
        return (TokenInfo(*t) for t in tokenize.generate_tokens(*args, **kwargs))

    # ripped from six https://bitbucket.org/gutworth/six
    exec("""def reraise(tp, value, tb=None):
        try:
            raise tp, value, tb
        finally:
            tb = None
    """)


elif is_py3:
    basestring = (str, bytes)
    unicode = str

    range = range

    from collections.abc import Callable, Iterable, Set, KeysView
    import queue
    import _thread
    from io import StringIO
    import inspect
    import builtins

    import tokenize
    from tokenize import tokenize as tokenizer

    # ripped from six https://bitbucket.org/gutworth/six
    def reraise(tp, value, tb=None):
        try:
            if value is None:
                value = tp()
            if value.__traceback__ is not tb:
                raise value.with_traceback(tb)
            raise value
        finally:
            value = None
            tb = None


String = unicode if is_py2 else str
Bytes = str if is_py2 else bytes

