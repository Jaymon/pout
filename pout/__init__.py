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

in the future, to list method arguments:
link -- http://stackoverflow.com/questions/3517892/python-list-function-argument-names

should take a look at this in more detail:
link -- http://docs.python.org/library/repr.html

module finder might be useful someday
link -- http://docs.python.org/library/modulefinder.html
link -- http://stackoverflow.com/questions/2572582/return-a-list-of-imported-python-modules-used-in-a-script

since -- 6-26-12
author -- Jay Marcyes
license -- MIT -- http://www.opensource.org/licenses/mit-license.php
"""
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import sys
import traceback
import ast
import re
import collections
import types
import time
import math
import unicodedata
import logging
import json
import platform
import resource
import codecs
import inspect

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
from .utils import String
from .reflect import Call, Reflect


__version__ = '0.8.0'


# This is the standard logger for debugging pout itself, if it hasn't been
# messed with we will set it to warning so it won't print anything out
logger = logging.getLogger(__name__)
# don't try and configure the logger for default if it has been configured elsewhere
# http://stackoverflow.com/questions/6333916/python-logging-ensure-a-handler-is-added-only-once
if len(logger.handlers) == 0:
    logger.setLevel(logging.WARNING)
    logger.addHandler(logging.NullHandler())


# this is the pout printing logger, if it hasn't been touched it will be
# configured to print to stderr, this is what is used in pout_class._print()
# TODO -- make this configurable to dump to a file
stream = logging.getLogger("{}.stream".format(__name__))
if len(stream.handlers) == 0:
    stream.setLevel(logging.DEBUG)
    log_handler = logging.StreamHandler(stream=sys.stderr)
    log_formatter = logging.Formatter('%(message)s')
    log_handler.setFormatter(log_formatter)
    stream.addHandler(log_handler)
    stream.propagate = False


class Logging(object):
    """Logging context manager used in pout.l()

    This will turn logging to the stderr on for everything inside the with block

    :Example:
        with Logging():
            logger.debug("This will print to the screen even if logging is off")
        logger.debug("this will not print if logging is off")

    similar to:
    https://github.com/python/cpython/blob/d918bbda4bb201c35d1ded3dde686d8b00a91851/Lib/unittest/case.py#L297
    """
    @property
    def loggers(self):
        """Return all the loggers that should be activated"""
        ret = []
        if self.logger_name:
            if isinstance(self.logger_name, logging.Logger):
                ret.append((self.logger_name.name, self.logger_name))
            else:
                ret.append((self.logger_name, logging.getLogger(self.logger_name)))

        else:
            ret = list(logging.Logger.manager.loggerDict.items())
            ret.append(("root", logging.getLogger()))
        return ret

    def __init__(self, logger_name="", level=logging.DEBUG):
        self.logger_name = logger_name

        if isinstance(level, basestring):
            if is_py2:
                self.level = logging._checkLevel(level.upper())
            else:
                self.level = logging._nameToLevel[level.upper()]

        else:
            self.level = level

    def __enter__(self):
        old_loggers = collections.defaultdict(dict)
        for logger_name, logger in self.loggers:
            try:
                old_loggers[logger_name]["handlers"] = logger.handlers[:]
                old_loggers[logger_name]["level"] = logger.level
                old_loggers[logger_name]["propagate"] = logger.propagate

                handler = logging.StreamHandler(stream=sys.stderr)
                #handler.setFormatter(formatter)
                logger.handlers = [handler]
                logger.setLevel(self.level)
                logger.propagate = False

            except AttributeError:
                pass


        self.old_loggers = old_loggers
        return self

    def __exit__(self, *args, **kwargs):
        for logger_name, logger_dict in self.old_loggers.items():
            logger = logging.getLogger(logger_name)
            for name, val in logger_dict.items():
                if name == "level":
                    logger.setLevel(val)
                else:
                    setattr(logger, name, val)


class Profiler(object):
    """this is a context manager for Profiling

    see -- p()
    since -- 10-21-2015
    """

    # profiler p() state is held here
    stack = []

    def __init__(self, name, call_info):
        self.start(name, call_info)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pr_class = type(self)
        if len(pr_class.stack) > 0:
            d = pr_class.stack.pop()
            d.stop()

            global pout_class
            p = pout_class.create_instance()
            p._print(d.calls, None)

    def start(self, name, call_info):
        self.start = time.time()
        self.name = name
        self.start_call_info = call_info
        type(self).stack.append(self)

    def stop(self, call_info=None):
        name = self.name
        p = pout_class.create_instance()
        if len(type(self).stack) > 0:
            name = ' > '.join((d.name for d in type(self).stack))
            name += ' > {}'.format(self.name)

        #d = type(self).stack.pop()
        self.stop = time.time()
        self.elapsed = self.get_elapsed(self.start, self.stop, 1000.00, 1)
        self.total = "{:.1f} ms".format(self.elapsed)

        summary = []
        summary.append("{} - {}".format(name, self.total))
        summary.append("  start: {} ({}:{})".format(
            self.start,
            p._get_path(self.start_call_info['file']),
            self.start_call_info['line']
        ))
        if call_info:
            summary.append("  stop: {} ({}:{})".format(
                self.stop,
                p._get_path(call_info['file']),
                call_info['line']
            ))
            self.call_info = call_info
        else:
            summary.append("  stop: {}".format(self.stop))
            self.call_info = self.start_call_info

        self.calls = [os.linesep.join(summary)]

    def get_elapsed(self, start, stop, multiplier, rnd):
        return round(abs(stop - start) * float(multiplier), rnd)


class Pout(object):
    """the main printing class, an instance of this class will be used to do
    pretty much everything.

    you can extend this class and change the `pout_class` global variable in
    order to use your child class
    """
    call_class = Call

    path_class = Path

    reflect_class = Reflect

    @classmethod
    def create_instance(cls):
        """every module function will call this, that way a customized class will 
        be picked up automatically"""
        return cls()

    def _get_arg_info(self, funcname="", arg_vals=None):
        c = self.reflect_class(
            modname=__name__,
            funcname=funcname,
            arg_vals=arg_vals
        )
        return c.info

    def _get_path(self, path):
        return self.path_class(path)

    def _print(self, args, call_info=None):
        '''
        handle printing args to the screen

        this uses the global logger, so you can configure where output goes by configuring the "pout"
        pythong logger

        args -- list -- the list of unicode args to print
        call_info -- dict -- returned from _get_arg_info()
        '''
        s = self._printstr(args, call_info)
        stream.debug(s)

    def _printstr(self, args, call_info=None):
        """this gets all the args ready to be printed, see self._print()"""
        # unicode sandwich, everything printed should be a byte string
        s = "\n"

        for arg in args:
            #s += arg.encode('utf-8', 'pout.replace')
            s += arg

        if call_info:
            s += "({}:{})\n\n".format(self._get_path(call_info['file']), call_info['line'])

        return s
        #return s.encode('utf-8', 'pout.replace')

    def _str(self, name, val):
        '''
        return a string version of name = val that can be printed

        example -- 
            _str('foo', 'bar') # foo = bar

        name -- string -- the variable name that was passed into one of the public methods
        val -- mixed -- the variable at name's value

        return -- string
        '''
        s = ''

        if name:

            try:
                count = len(val)
                s = "{} ({}) = {}".format(name, count, self._str_val(val, depth=0))
            except (TypeError, KeyError, AttributeError):
                pass

            if not s:
                s = "{} = {}".format(name, self._str_val(val))

        else:
            s = self._str_val(val)

        return s

    def _str_val(self, val, depth=0):
        '''
        turn val into a string representation of val

        val -- mixed -- the value that will be turned into a string
        depth -- integer -- how many levels of recursion we've done

        return -- string
        '''
        vt = Value(val)
        s = "{}".format(vt)
        return s

    def _get_backtrace(self, frames, inspect_packages=False, depth=0):
        '''
        get a nicely formatted backtrace

        since -- 7-6-12

        frames -- list -- the frame_tuple frames to format
        inpsect_packages -- boolean -- by default, this only prints code of packages that are not 
            in the pythonN directories, that cuts out a lot of the noise, set this to True if you
            want a full stacktrace
        depth -- integer -- how deep you want the stack trace to print (ie, if you only care about
            the last three calls, pass in depth=3 so you only get the last 3 rows of the stack)

        return -- list -- each line will be a nicely formatted entry of the backtrace
        '''
        calls = []
        count = 1

        for i, f in enumerate(frames[1:]):
            prev_f = frames[i]
            called_module = inspect.getmodule(prev_f[0]).__name__
            called_func = prev_f[3]

            d = self.call_class(f, called_module, called_func).info
            s = self._get_call_summary(d, inspect_packages=inspect_packages, index=count)
            calls.append(s)
            count += 1

            if depth and (count > depth):
                break

        # reverse the order on return so most recent is on the bottom
        return calls[::-1]

    def _get_call_summary(self, call_info, index=0, inspect_packages=True):
        '''
        get a call summary

        a call summary is a nicely formatted string synopsis of the call

        handy for backtraces

        since -- 7-6-12

        call_info -- dict -- the dict returned from _get_call_info()
        index -- integer -- set to something above 0 if you would like the summary to be numbered
        inspect_packages -- boolean -- set to True to get the full format even for system frames

        return -- string
        '''
        inspect_regex = re.compile(r'[\\\\/]python\d(?:\.\d+)?', re.I)

        # truncate the filepath if it is super long
        f = call_info['file']
        if len(f) > 75:
            f = "{}...{}".format(f[0:30], f[-45:])

        if inspect_packages or not inspect_regex.search(call_info['file']): 

            s = "{}:{}\n\n{}\n\n".format(
                f,
                call_info['line'],
                String(call_info['call']).indent(1)
            )

        else:

            s = "{}:{}\n".format(
                f,
                call_info['line']
            )

        if index > 0:
            s = "{:02d} - {}".format(index, s)

        return s

    def t(self, inspect_packages=False, depth=0):
        '''
        print a backtrace

        since -- 7-6-12

        inpsect_packages -- boolean -- by default, this only prints code of packages that are not 
            in the pythonN directories, that cuts out a lot of the noise, set this to True if you
            want a full stacktrace
        depth -- integer -- how deep you want the stack trace to print (ie, if you only care about
            the last three calls, pass in depth=3 so you only get the last 3 rows of the stack)
        '''
        frame = inspect.currentframe()
        frames = inspect.getouterframes(frame)
        call_info = self._get_arg_info("t")
        calls = self._get_backtrace(frames=frames, inspect_packages=inspect_packages, depth=depth)
        self._print(calls, call_info)

    def p(self, name=None):
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
        d = None
        if name:
            d = Profiler(String(name), self._get_arg_info("p"))

        else:
            if len(Profiler.stack) > 0:
                d = Profiler.stack[-1]
                d.__exit__()

        return d

    def m(self, name=''):
        """
        Print out memory usage at this point in time

        http://docs.python.org/2/library/resource.html
        http://stackoverflow.com/a/15448600/5006
        http://stackoverflow.com/questions/110259/which-python-memory-profiler-is-recommended
        """
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # according to the docs, this should give something good but it doesn't jive
        # with activity monitor, so I'm using the value that gives me what activity 
        # monitor gives me
        # http://docs.python.org/2/library/resource.html#resource.getpagesize
        # (usage[2] * resource.getpagesize()) / (1024 * 1024)
        # http://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python
        rss = 0.0
        platform_name = platform.system()
        if platform_name == 'Linux':
            # linux seems to return KB, while OSX returns B
            rss = float(usage[2]) / 1024.0
        else:
            rss = float(usage[2]) / (1024.0 * 1024.0)

        call_info = self._get_arg_info("m")
        summary = ''
        if name:
            summary += "{}: ".format(name)

        summary += "{0} mb{1}{1}".format(round(rss, 2), os.linesep)
        calls = [summary]
        self._print(calls, call_info)

    def j(self, *args):
        """
        dump json

        since -- 2013-9-10

        *args -- tuple -- one or more json strings to dump
        """
        assert len(args) > 0, "you didn't pass any arguments to print out"

        call_info = self._get_arg_info("j", args)
        args = ["{}\n\n".format(self._str(v['name'], json.loads(v['val']))) for v in call_info['args']]
        self._print(args, call_info)

    def b(self, *args):
        '''
        create a big text break, you just kind of have to run it and see

        since -- 2013-5-9

        *args -- 1 arg = title if string, rows if int
            2 args = title, int
            3 args = title, int, sep
        '''
        lines = []

        title = ''
        rows = 1
        sep = '*'

        if len(args) == 1:
            if Value(args[0]).typename in set(['STRING', 'BINARY']):
                title = args[0]
            else:
                rows = int(args[0])
        elif len(args) == 2:
            title = args[0]
            rows = args[1]
        elif len(args) == 3:
            title = args[0]
            rows = args[1]
            sep = String(args[2])

        if not rows: rows = 1
        half_rows = int(math.floor(rows / 2))
        is_even = (rows >= 2) and ((rows % 2) == 0)

        line_len = title_len = 80
        if title:
            title = ' {} '.format(String(title))
            title_len = len(title)
            if title_len > line_len:
                line_len = title_len

            for x in range(half_rows):
                lines.append(sep * line_len)

            lines.append(title.center(line_len, sep))

            for x in range(half_rows):
                lines.append(sep * line_len)

        else:
            for x in range(rows):
                lines.append(sep * line_len)

        lines.append('')
        call_info = self._get_arg_info("b")
        self._print([os.linesep.join(lines)], call_info)

    def c(self, *args):
        '''
        kind of like od -c on the command line, basically it dumps each character and info
        about that char

        since -- 2013-5-9

        *args -- tuple -- one or more strings to dump
        '''
        lines = []
        call_info = self._get_arg_info("c")
        for arg in args:
            arg = String(arg)
            lines.append('Total Characters: {}'.format(len(arg)))
            for i, c in enumerate(arg, 1):

                line = ['{}.'.format(i)]
                if c == '\n':
                    line.append('\\n')
                elif c == '\r':
                    line.append('\\r')
                elif c == '\t':
                    line.append('\\t')
                else:
                    line.append(c)

                line.append(repr(c.encode('utf-8')))

                cint = ord(c)
                if cint > 65535:
                    line.append('\\U{:0>8X}'.format(cint))
                else:
                    line.append('\\u{:0>4X}'.format(cint))

                line.append(unicodedata.name(c, 'UNKNOWN'))
                lines.append('\t'.join(line))

            lines.append('')
            lines.append('')

        self._print([os.linesep.join(lines)], call_info)

    def x(self, exit_code=1):
        '''
        same as sys.exit(1) but prints out where it was called from before exiting

        I just find this really handy for debugging sometimes

        since -- 2013-5-9

        exit_code -- int -- if you want it something other than 1
        '''
        call_info = self._get_arg_info("x")
        self._print(['exit '], call_info)
        sys.exit(exit_code)

    def h(self, count=0):
        '''
        prints "here count"

        example -- 
            h(1) # here 1 (/file:line)
            h() # here line (/file:line)

        count -- integer -- the number you want to put after "here"
        '''
        call_info = self._get_arg_info("h")
        args = ["here {} ".format(count if count > 0 else call_info['line'])]
        self._print(args, call_info)

    def vv(self, *args):
        """
        exactly like v, but doesn't print variable names or file positions (useful for logging)
        """
        assert len(args) > 0, "you didn't pass any arguments to print out"

        call_info = self._get_arg_info("vv", args)
        args = ["{}\n\n".format(self._str(None, v['val'])) for v in call_info['args']]
        self._print(args)

    def v(self, *args):
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
        assert len(args) > 0, "you didn't pass any arguments to print out"

        call_info = self._get_arg_info("v", args)
        args = ["{}\n\n".format(self._str(v['name'], v['val'])) for v in call_info['args']]
        self._print(args, call_info)

    def ss(self, *args):
        """
        exactly like s, but doesn't return variable names or file positions (useful for logging)

        since -- 10-15-2015
        return -- str
        """
        assert len(args) > 0, "you didn't pass any arguments"
        call_info = self._get_arg_info("ss", args)
        args = ["{}\n\n".format(self._str(None, v['val'])) for v in call_info['args']]
        return self._printstr(args)

    def s(self, *args):
        """
        exactly like v() but returns the string instead of printing it out

        since -- 10-15-2015
        return -- str
        """
        assert len(args) > 0, "you didn't pass any arguments"
        call_info = self._get_arg_info("s", args)
        args = ["{}\n\n".format(self._str(v['name'], v['val'])) for v in call_info['args']]
        return self._printstr(args, call_info)

    def sleep(self, seconds):
        '''
        same as time.sleep(seconds) but prints out where it was called before sleeping
        and then again after finishing sleeping

        I just find this really handy for debugging sometimes

        since -- 2017-4-27

        :param seconds: float|int, how many seconds to sleep
        '''
        if seconds <= 0: return

        call_info = self._get_arg_info("sleep")
        args = ["Sleeping {} second{} at {}:{}".format(
            seconds,
            "s" if seconds > 1 else "",
            call_info["file"],
            call_info["line"]
        )]
        self._print(args)

        time.sleep(seconds)

        args = ["Done Sleeping "]
        self._print(args, call_info)

    def i(self, *args):
        if len(args) <= 0:
            raise ValueError("you didn't pass any arguments to print out")

        call_info = self._get_arg_info("i", args)
        pargs = []
        methods = []
        properties = []
        for v in call_info["args"]:
            vt = Value(v['val'])
            full_info = self._str(v['name'], vt.info())
            pargs.append(full_info)

        self._print(pargs, call_info)

    def l(self, *args, **kwargs):
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
        return Logging(*args, **kwargs)


# this can be changed after import to customize functionality
pout_class = Pout


# these are the mappings to make the instance methods look like module level
# functions. Check the corresponding Pout method for information about what each of
# these functions/methods do
def b(*args, **kwargs):
    return pout_class.create_instance().b(*args, **kwargs)
def c(*args, **kwargs):
    return pout_class.create_instance().c(*args, **kwargs)
def h(*args, **kwargs):
    return pout_class.create_instance().h(*args, **kwargs)
def j(*args, **kwargs):
    return pout_class.create_instance().j(*args, **kwargs)
def m(*args, **kwargs):
    return pout_class.create_instance().m(*args, **kwargs)
def p(*args, **kwargs):
    return pout_class.create_instance().p(*args, **kwargs)
def s(*args, **kwargs):
    return pout_class.create_instance().s(*args, **kwargs)
def ss(*args, **kwargs):
    return pout_class.create_instance().ss(*args, **kwargs)
def t(*args, **kwargs):
    return pout_class.create_instance().t(*args, **kwargs)
def v(*args, **kwargs):
    return pout_class.create_instance().v(*args, **kwargs)
def vv(*args, **kwargs):
    return pout_class.create_instance().vv(*args, **kwargs)
def x(*args, **kwargs):
    return pout_class.create_instance().x(*args, **kwargs)
def sleep(*args, **kwargs):
    return pout_class.create_instance().sleep(*args, **kwargs)
def i(*args, **kwargs):
    return pout_class.create_instance().i(*args, **kwargs)
def l(*args, **kwargs):
    return pout_class.create_instance().l(*args, **kwargs)


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


