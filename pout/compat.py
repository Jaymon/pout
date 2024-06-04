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


String = unicode if is_py2 else str
Bytes = str if is_py2 else bytes

