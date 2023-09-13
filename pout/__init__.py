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
import sys
import logging

from . import environ
#from .compat import *
from .utils import StderrStream
from .reflect import Call, Reflect
from .interface import Interface
from .value import Value


__version__ = '2.3.0'


# This is the standard logger for debugging pout itself, if it hasn't been
# messed with we will set it to warning so it won't print anything out
logger = logging.getLogger(__name__)
# don't try and configure the logger for default if it has been configured elsewhere
# http://stackoverflow.com/questions/6333916/python-logging-ensure-a-handler-is-added-only-once
if len(logger.handlers) == 0:
    # set to True to turn on all logging:
    if environ.DEBUG:
        logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(stream=sys.stderr)
        log_handler.setFormatter(logging.Formatter('[%(levelname).1s] %(message)s'))
        logger.addHandler(log_handler)

    else:
        logger.setLevel(logging.WARNING)
        logger.addHandler(logging.NullHandler())


# this is the pout printing logger, you can modify the logger this instance uses
# or completely replace it to customize functionality
stream = StderrStream()


# This will inject functions into the pout module, so if you're wondering where
# the pout.v() method is, look at the pout.interface.V class
Interface.inject_classes()


def inject():
    """Injects pout into the builtins module so it can be called from anywhere without
    having to be explicitly imported, this is really just for convenience when
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


