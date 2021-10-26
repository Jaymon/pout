# -*- coding: utf-8 -*-
"""
prints out variables and other handy things to help with debugging

print was too hard to read, pprint wasn't much better. I was getting sick of typing: 
print "var name: {}".format(var). This tries to print out variables with their name, 
and where the print statement was called (so you can easily find it and delete it later).

link -- http://stackoverflow.com/questions/3229419/pretty-printing-nested-dictionaries-in-python
link -- http://docs.python.org/library/pprint.html
link -- http://docs.python.org/library/inspect.html
link -- http://www.doughellmann.com/PyMOTW/inspect/

should take a look at this in more detail (repr in py2, reprlib in py3):
link -- http://docs.python.org/2.7/library/repr.html

since -- 6-26-12
"""
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import sys
import time
import logging
from contextlib import contextmanager

from . import environ
from .compat import *
from .utils import String, StderrStream, FileStream
from .reflect import Call, Reflect
from .interface import Interface


__version__ = '2.0.0'


# This is the standard logger for debugging pout itself, if it hasn't been
# messed with we will set it to warning so it won't print anything out
logger = logging.getLogger(__name__)
# don't try and configure the logger for default if it has been configured elsewhere
# http://stackoverflow.com/questions/6333916/python-logging-ensure-a-handler-is-added-only-once
if len(logger.handlers) == 0:
    logger.setLevel(logging.WARNING)
    logger.addHandler(logging.NullHandler())

    # set to True to turn on all logging:
    if environ.DEBUG:
        logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(stream=sys.stderr)
        log_handler.setFormatter(logging.Formatter('[%(levelname).1s] %(message)s'))
        logger.addHandler(log_handler)


# this is the pout printing logger, you can modify the logger this instance uses
# or completely replace it to customize functionality
stream = StderrStream()


@contextmanager
def tofile(path=""):
    """Instead of printing to a screen print to a file

    :Example:
        with pout.tofile("/path/to/file.txt"):
            # all pout calls in this with block will print to file.txt
            pout.v("a string")
            pout.b()
            pout.h()

    :param path: str, a path to the file you want to write to
    """
    if not path:
        path = os.path.join(os.getcwd(), "{}.txt".format(__name__))

    global stream
    orig_stream = stream

    try:
        stream = FileStream(path)
        yield stream

    finally:
        stream = orig_stream
f = tofile



# def inject_interface():
#     Interface.inject_classes()
#     #inters = Interfaces()
#     #inters.inject()
#     #ValueInterface.inject()
#     #module = sys.modules[__name__]
#     #setattr(module, "foo", inters)
# inject_interface()


# This will inject functions into the pout module
Interface.inject_classes()


def inject():
    """Injects pout into the builtins module so it can be called from anywhere without
    having to be explicitely imported, this is really just for convenience when
    debugging

    https://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable
    """
    try:
        from .compat import builtins

        module = sys.modules[__name__]
        setattr(builtins, __name__, module)
        #builtins.pout = pout

    except ImportError:
        pass


