# -*- coding: utf-8 -*-
"""
prints out variables and other handy things to help with debugging

print was too hard to read, pprint wasn't much better. I was getting sick of
typing: print "var name: {}".format(var). This tries to print out variables
with their name, and where the print statement was called (so you can easily
find it and delete it later).

link -- http://stackoverflow.com/questions/3229419/pretty-printing-nested-dictionaries-in-python
link -- http://docs.python.org/library/pprint.html
link -- http://docs.python.org/library/inspect.html
link -- http://www.doughellmann.com/PyMOTW/inspect/

should take a look at this in more detail (repr in py2, reprlib in py3):
link -- http://docs.python.org/2.7/library/repr.html

since -- 6-26-12
"""
import sys
import logging
import functools

from . import environ
#from .compat import *
from .utils import StderrStream
from .reflect import Call, Reflect
from .interface import Interface
from .value import Value


__version__ = '3.2.0'


# This is the standard logger for debugging pout itself, if it hasn't been
# messed with we will set it to warning so it won't print anything out
logger = logging.getLogger(__name__)

# don't try and configure the logger for default if it has been configured
# elsewhere
# http://stackoverflow.com/questions/6333916/python-logging-ensure-a-handler-is-added-only-once
if len(logger.handlers) == 0:
    # set to True to turn on all logging:
    if environ.DEBUG:
        logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(stream=sys.stderr)
        log_handler.setFormatter(
            logging.Formatter('[%(levelname).1s] %(message)s')
        )
        logger.addHandler(log_handler)

    else:
        logger.setLevel(logging.WARNING)
        logger.addHandler(logging.NullHandler())


# this is the pout printing logger, you can modify the logger this instance
# uses or completely replace it to customize functionality
stream = StderrStream()


def __getattr__(name):
    """This uses Interface.classes to match a function call on pout to an
    Interface class

    If you're wondering where the `pout.v()` function is, look at the
    `pout.interface.V` class

    :param name: str, the pout function name (eg, `pout.v`) that will match
        to an Interface class (eg, `pout.v` will match to `pout.interface.V`)
    :returns: callable
    """
    interface_class = Interface.classes[name]
    module = interface_class.get_module()

    func = functools.partial(
        interface_class.create_instance,
        pout_module=module,
        pout_function_name=name,
        pout_interface_class=interface_class,
    )
    func.__name__ = name
    func.__module__ = module
    return func


def inject():
    """Injects pout into the builtins module so it can be called from anywhere
    without having to be explicitly imported, this is really just for
    convenience when debugging

    https://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable
    """
    try:
        from .compat import builtins

        module = sys.modules[__name__]
        setattr(builtins, __name__, module)
        #builtins.pout = pout

    except ImportError:
        pass


