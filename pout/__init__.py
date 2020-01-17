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
from .compat import (
    is_py2,
    is_py3,
    unicode,
    basestring,
    inspect,
    range,
    Callable,
    Iterable,
    Set,
)
from .value import Inspect, Value
from .path import Path
from .utils import String, StderrStream, FileStream
from .reflect import Call, Reflect
from .interface import (
    ValueInterface,
    HereInterface,
    BreakInterface,
    CharInterface,
    JsonInterface,
    MemoryInterface,
    ProfileInterface,
    LoggingInterface,
    InfoInterface,
    TraceInterface,
    RowInterface,
)


__version__ = '0.8.13'


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


# these can be changed after import to customize functionality
V_CLASS = ValueInterface
H_CLASS = HereInterface
B_CLASS = BreakInterface
C_CLASS = CharInterface
J_CLASS = JsonInterface
M_CLASS = MemoryInterface
P_CLASS = ProfileInterface
L_CLASS = LoggingInterface
I_CLASS = InfoInterface
T_CLASS = TraceInterface
R_CLASS = RowInterface


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


def v(*args, **kwargs):
    '''
    print the name = values of any passed in variables

    this prints out the passed in name, the value, and the file:line where the v()
    method was called so you can easily find it and remove it later

    example -- 
        foo = 1
        bar = [1, 2, 3]
        out.v(foo, bar)
        """ prints out:
        foo = 1

        bar = 
        [
            0: 1,
            1: 2,
            2: 3
        ]

        (/file:line)
        """

    *args -- list -- the variables you want to see pretty printed for humans
    '''
    if not args:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = V_CLASS(r, stream, **kwargs)
        instance()


def vs(*args, **kwargs):
    """
    exactly like v, but doesn't print variable names or file positions

    .. seealso:: ss()
    """
    if not args:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = V_CLASS(r, stream, **kwargs)
        instance.writeline(instance.value())
vv = vs


def s(*args, **kwargs):
    """
    exactly like v() but returns the string instead of printing it out

    since -- 10-15-2015
    return -- str
    """
    if not args:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = V_CLASS(r, stream, **kwargs)
        return instance.full_value().strip()


def ss(*args, **kwargs):
    """
    exactly like s, but doesn't return variable names or file positions (useful for logging)

    since -- 10-15-2015
    return -- str
    """
    if not args:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = V_CLASS(r, stream, **kwargs)
        return instance.value().strip()


def i(*args, **kwargs):
    if len(args) <= 0:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = I_CLASS(r, stream, **kwargs)
        instance()


def r(*args, **kwargs):
    """Similar to pout.v() but gets rid of name and file information so it can be used
    in loops and stuff, it will print out where the calls came from at the end of
    execution

    this just makes it nicer when you're printing a bunch of stuff each iteration

    :Example:
        for x in range(x):
            pout.r(x)
    """

    if len(args) <= 0:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = R_CLASS(r, stream, **kwargs)
        instance()


def x(*args, **kwargs):
    '''
    same as sys.exit(1) but prints out where it was called from before exiting

    I just find this really handy for debugging sometimes

    since -- 2013-5-9

    exit_code -- int -- if you want it something other than 1
    '''
    with Reflect.context(args, **kwargs) as r:
        instance = V_CLASS(r, stream, **kwargs)
        if args:
            instance()

        else:
            instance.writelines([
                'exit at line {}\n'.format(instance.reflect.info["line"]),
                instance.path_value()
            ])

    exit_code = 1
    sys.exit(exit_code)


def h(count=0, **kwargs):
    '''
    prints "here count"

    example -- 
        h(1) # here 1 (/file:line)
        h() # here line (/file:line)

    count -- integer -- the number you want to put after "here"
    '''
    with Reflect.context(**kwargs) as r:
        kwargs["count"] = count
        instance = H_CLASS(r, stream, **kwargs)
        instance()


def b(*args, **kwargs):
    '''
    create a big text break, you just kind of have to run it and see

    since -- 2013-5-9

    *args -- 1 arg = title if string, rows if int
        2 args = title, int
        3 args = title, int, sep
    '''
    with Reflect.context(**kwargs) as r:
        kwargs["args"] = args
        instance = B_CLASS(r, stream, **kwargs)
        instance()


def c(*args, **kwargs):
    '''
    kind of like od -c on the command line, basically it dumps each character and info
    about that char

    since -- 2013-5-9

    *args -- tuple -- one or more strings to dump
    '''
    with Reflect.context(**kwargs) as r:
        kwargs["args"] = args
        instance = C_CLASS(r, stream, **kwargs)
        instance()


def j(*args, **kwargs):
    """
    dump json

    since -- 2013-9-10

    *args -- tuple -- one or more json strings to dump
    """
    if not args:
        raise ValueError("you didn't pass any arguments to print out")

    with Reflect.context(args, **kwargs) as r:
        instance = J_CLASS(r, stream, **kwargs)
        instance()


def m(name='', **kwargs):
    """
    Print out memory usage at this point in time

    http://docs.python.org/2/library/resource.html
    http://stackoverflow.com/a/15448600/5006
    http://stackoverflow.com/questions/110259/which-python-memory-profiler-is-recommended
    """
    with Reflect.context(**kwargs) as r:
        kwargs["name"] = name
        instance = M_CLASS(r, stream, **kwargs)
        instance()


def p(name="", **kwargs):
    '''
    really quick and dirty profiling

    you start a profile by passing in name, you stop the top profiling by not
    passing in a name. You can also call this method using a with statement

    This is for when you just want to get a really back of envelope view of
    how your fast your code is, super handy, not super accurate

    since -- 2013-5-9
    example --
        p("starting profile")
        time.sleep(1)
        p() # stop the "starting profile" session

        # you can go N levels deep
        p("one")
        p("two")
        time.sleep(0.5)
        p() # stop profiling of "two"
        time.sleep(0.5)
        p() # stop profiling of "one"

        with pout.p("three"):
            time.sleep(0.5)

    name -- string -- pass this in to start a profiling session
    return -- context manager
    '''
    with Reflect.context(**kwargs) as r:
        if name:
            instance = P_CLASS(r, stream, name, **kwargs)
        else:
            instance = P_CLASS.pop(r)
            instance()

    return instance


def sleep(seconds, **kwargs):
    '''
    same as time.sleep(seconds) but prints out where it was called before sleeping
    and then again after finishing sleeping

    I just find this really handy for debugging sometimes

    since -- 2017-4-27

    :param seconds: float|int, how many seconds to sleep
    '''
    if seconds <= 0.0:
        raise ValueError("Invalid seconds {}".format(seconds))

    with Reflect.context(**kwargs) as r:
        instance = V_CLASS(r, stream, **kwargs)
        instance.writeline("Sleeping {} second{} at {}".format(
            seconds,
            "s" if seconds != 1.0 else "",
            instance.path_value()
        ))

        time.sleep(seconds)
        instance.writelines(["...Done Sleeping\n", instance.path_value()])


def l(*args, **kwargs):
    """see Logging class for details, this is just the method wrapper around Logging

    :Example:
        # turn on logging for all loggers
        with pout.l():
            # do stuff that produces logs and see it prints to stderr

        # turn on logging just for a specific logger
        with pout.l("name"):
            # "name" logger will print to stderr, all other loggers will act
            # as configured

    :param logger_name: string|Logger, the logger name you want to print to stderr
    :param level: string|int, the logging level the logger should be set at,
        this defaults to logging.DEBUG
    """
    return LoggingInterface(*args, **kwargs)


def t(inspect_packages=False, depth=0, **kwargs):
    '''
    print a backtrace

    since -- 7-6-12

    inpsect_packages -- boolean -- by default, this only prints code of packages that are not 
        in the pythonN directories, that cuts out a lot of the noise, set this to True if you
        want a full stacktrace
    depth -- integer -- how deep you want the stack trace to print (ie, if you only care about
        the last three calls, pass in depth=3 so you only get the last 3 rows of the stack)
    '''


    #frame = inspect.currentframe()

    try:
        frames = inspect.stack()
        kwargs["frames"] = frames
        kwargs["inspect_packages"] = inspect_packages
        kwargs["depth"] = depth

        with Reflect.context(**kwargs) as r:
            instance = T_CLASS(r, stream, **kwargs)
            instance()

    finally:
        del frames


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


