# -*- coding: utf-8 -*-
"""
The pout functions like pout.v() use the interfaces that are defined in this module
to print an object out
"""
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import sys
import math
import unicodedata
try:
    import resource
except ImportError:
    resource = None
import platform
import time
import logging
import collections
import re
import atexit
from collections import defaultdict, Counter
import json
import traceback
import functools

from .compat import *
from . import environ
from .value import Value, ObjectValue
from .path import Path
from .utils import String, Bytes, FileStream
from .reflect import Call, Reflect


logger = logging.getLogger(__name__)


class Interface(object):
    """Most of pout's output will go through some child of this class

    To add a new pout function, you would extend this class and the class name
    would be the name of the function, so if you did:

        class Foo(Interface):
            def __call__(self, *args, **kwargs):
                self.writeline(f"Foo called with {len(args)} args and {len(kwargs) kwargs})"

    Then you could do:

        pout.foo(1, 2, 3, bar=4)

    Interface has a default call that tries to handle everything and so the only
    method you might need to mess with is .body_value(self, body, **kwargs)
    """
    path_class = Path

    SHOW_META = True
    """If False then name and path will not be added to a value"""

    SHOW_NAME = True
    """If False then name will not be added to the beginning of a value"""

    SHOW_PATH = True
    """If False then path will not be added to the end of a value"""

    PRINT_OUTPUT = True
    """If True then .output() will be printed using .stream"""

    RETURN_OUTPUT = False
    """If True then .output() will be returned"""

    @classmethod
    def function_name(cls):
        """returns the name that pout will use to interface with an instance of this
        class

        :returns: string, the class name, by default, this is just the class name
            lowercased
        """
        function_name = String(cls.__name__).snakecase().lower()
        return function_name

    @classmethod
    def module_name(cls):
        """Returns the default module name

        :returns: str, the default module name, which will usually be `pout`
        """
        return __name__.split(".")[0]

    @classmethod
    def get_module(cls, module=None):
        """Returns either the passed in module or the default module

        :param module: module, this module will override the default module
        :returns: module
        """
        return module or sys.modules[cls.module_name()]

    @classmethod
    def create_instance(cls, *args, **kwargs):
        """This is the hook, basically pout.<FUNCTION_NAME> will actually call
        this method, and this method will, in turn, call __call__

        :param *args: mixed, the arguments passed to pout.<FUNCTION_NAME>
        :param **kwargs: mixed, the keyword arguments passed to pout.<FUNCTION_NAME>
            plus some other arguments that were bound to <FUNCTION_NAME> like
            `pout_module` and `pout_function_name`
        :returns: mixed, whatever __call__ returns
        """
        module = kwargs["pout_module"]
        module_function_name = kwargs["pout_function_name"]
        instance_class = kwargs["pout_interface_class"]

        with Reflect(module, module_function_name, args) as r:
            instance = instance_class(r, module.stream)
            return instance(*args, **kwargs)

    @classmethod
    def find_classes(cls, cutoff_class=None):
        """Used by auto-discovery to find all the children of Interface

        :param cutoff_class: object, this method will only find children of this
            class, if not passed in then it will be set to Interface
        :returns: generator, yields all found classes
        """
        cutoff_class = cutoff_class or Interface
        module = sys.modules[__name__]
        for ni, vi in inspect.getmembers(module, inspect.isclass):
            if issubclass(vi, cutoff_class) and vi is not cutoff_class:
                yield vi

    @classmethod
    def inject_classes(cls, cutoff_class=None, module=None):
        """This will find all the children of cutoff_class and inject them into
        module as being callable at module.<FUNCTION_NAME>

        :param cutoff_class: see find_classes
        :param module: module, a python module that will be injected with the 
            found cutoff_class children. This will default to pout
        """
        module = cls.get_module(module)
        for inter_class in cls.find_classes(cutoff_class=cutoff_class):
            inter_class.inject(module)

    @classmethod
    def inject(cls, module=None):
        """Actually inject this cls into module"""
        module = cls.get_module(module)
        function_name = cls.function_name()
        logger.debug("Injecting {}.{} as {}.{} function".format(
            __name__,
            cls.__name__,
            module.__name__,
            function_name,
        ))
        func = functools.partial(
            cls.create_instance,
            pout_module=module,
            pout_function_name=function_name,
            pout_interface_class=cls,
        )
        func.__name__ = function_name
        func.__module__ = module
        setattr(module, function_name, func)

    def __init__(self, reflect, stream):
        self.reflect = reflect
        self.stream = stream

    def writeline(self, s):
        """Actually write s to something using self.stream"""
        self.stream.writeline(s)

    def writelines(self, ss):
        """Write a list of string to something using self.stream"""
        for s in ss:
            self.writeline(s)

    def _get_path(self, path):
        return self.path_class(path)

    def _printstr(self, args):
        """this gets all the args ready to be printed, this is terribly named"""
        s = "\n"

        for arg in args:
            #s += arg.encode('utf-8', 'pout.replace')
            s += arg

        return s

    def name_value(self, name, body, **kwargs):
        """normalize name. This will only do something with name if it has a value

        this method is called after .body_value(). This method respects SHOW_META
        and SHOW_NAME. This method will get called once for
        each tuple value [0] yielded from .input()

        :param name: str, the name value to use
        :param body: Any, the original un-normalized body, this is handy to have
            in case you want to tie the normalized name to the body in some way
        :param **kwargs: dict, anything passed into the interface
        :returns: str, the name normalized
        """
        s = ""
        if name:
            show_meta = kwargs.get("show_meta", self.SHOW_META)
            show_name = show_meta and kwargs.get("show_name", self.SHOW_NAME)
            if show_name:
                s = name
        return s

    def body_value(self, body, **kwargs):
        """normalize body

        this method is called from .output(). This method will get called once for
        each tuple value [1] yielded from .input()

        :param body: mixed, one of the inputted body
        :param **kwargs: dict, anything passed into the interface
        :returns: str, the body normalized
        """
        return body

    def path_value(self, **kwargs):
        """normalize and return the path the interface was called from

        This method respects SHOW_META and SHOW_PATH

        :param **kwargs: dict, anything passed into the interface
        :returns: str, the path that should be included with the .name_value() and
            .body_value() values
        """
        s = ""
        show_meta = kwargs.get("show_meta", self.SHOW_META)
        show_path = show_meta and kwargs.get("show_path", self.SHOW_PATH)
        if show_path:
            call_info = self.reflect.info
            if call_info:
                s = "({}:{})".format(
                    self._get_path(call_info['file']),
                    call_info['line']
                )
        return s

    def input(self, *args, **kwargs):
        """normalize the arguments passed into the interface

        this is called from .output() and is used by .output() to put together
        the full output

        :param *args: list, the arguments passed into the interface
        :param **kwargs: dict, the keyword arguments passed into the interface
        :returns: generator of tuples, this will yield a tuple of (name, body),
            either of the values can be None. If no arguments were passed in
            then this will yield one time with (None, None)
        """
        if args:
            for arg in args:
                yield None, arg

        else:
            # if we don't have any arguments we want .output() to do one iteration
            yield None, None

    def output(self, *args, **kwargs):
        """Iterates through .input() and converts it in a format that can be printed

        This will iterate through .input() and call .body_value() and .name_value()
        for each tuple yielded. After all input has been yielded this will call
        .path_value()

        :returns: str, a string ready to be printed or returned
        """
        bodies = []
        for n, b in self.input(*args, **kwargs):
            body = self.body_value(b, **kwargs)
            name = self.name_value(n, b, **kwargs)

            if name:
                bodies.append("{} = {}".format(name, body))

            else:
                bodies.append(body)

        path = self.path_value(**kwargs)
        if path:
            bodies.append(path)
        bodies.append("\n")

        return self._printstr(bodies)

    def __call__(self, *args, **kwargs):
        """Whenever a bound <FUNCTION_NAME> is invoked, this method is called

        This method respects PRINT_OUTPUT and RETURN_OUTPUT

        :param *args: mixed, the module.<FUNCTION_NAME> args
        :param **kwargs: mixed, the module.<FUNCTION_NAME> kwargs plus extra bound
            keywords
        :returns: mixed, whatever you want module.<FUNCTION_NAME> to return
        """
        kwargs.setdefault("print_output", self.PRINT_OUTPUT)
        kwargs.setdefault("return_output", self.RETURN_OUTPUT)

        s = self.output(*args, **kwargs)
        if kwargs["print_output"]:
            self.writeline(s)

        return s.strip() if kwargs["return_output"] else None


class V(Interface):
    '''
    print the name = values of any passed in variables

    this prints out the passed in name, the value, and the file:line where the v()
    method was called so you can easily find it and remove it later

    :example: 
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

    :param *args: list, the variables you want to see pretty printed for humans
    '''
    value_class = Value
    """the default class to use to introspect an input's value"""

    def create_value(self, value, **kwargs):
        value_class = kwargs.get("value_class", self.value_class)
        return value_class(value, **kwargs)

    def name_value(self, name, body, **kwargs):
        name = super().name_value(name, body, **kwargs)
        if name:
            value = self.create_value(body, **kwargs)
            name = value.name_value(name)
        return name

    def body_value(self, body, **kwargs):
        value = self.create_value(body, **kwargs)
        return value.string_value() + "\n"

    def input(self, *args, **kwargs):
        call_info = self.reflect.info
        if not call_info["args"]:
            raise ValueError("you didn't pass any arguments")

        for v in call_info["args"]:
            yield v["name"], v["val"]


class VS(V):
    """
    exactly like v, but doesn't print variable names or file positions

    .. seealso:: ss()
    """
    SHOW_META = False


class VV(VS):
    """alias of VS"""
    pass


class S(V):
    """
    exactly like v() but returns the string instead of printing it out

    since -- 10-15-2015
    return -- str
    """
    PRINT_OUTPUT = False
    RETURN_OUTPUT = True


class SS(S):
    """
    exactly like s, but doesn't return variable names or file positions (useful for logging)

    since -- 10-15-2015
    return -- str
    """
    SHOW_META = False


class X(V):
    '''same as v() but calls sys.exit() after printing values

    I just find this really handy for debugging sometimes

    since -- 2013-5-9
    https://github.com/Jaymon/pout/issues/50
    '''
    def __call__(self, *args, **kwargs):
        if not args:
            self.reflect.info["args"] = [{
                "name": None,
                "val": 'exit at line {}'.format(self.reflect.info["line"]),
            }]

        super().__call__(*args, **kwargs)
        exit_code = int(kwargs.get("exit_code", kwargs.get("code", 1)))
        sys.exit(exit_code)


class I(V):
    """Print out all class information (properties and methods) of the values"""
    def __call__(self, *args, **kwargs):
        kwargs.setdefault("show_methods", True)
        kwargs.setdefault("show_magic", True)
        kwargs.setdefault("value_class", ObjectValue)
        return super().__call__(*args, **kwargs)


class VI(I):
    """alias of I"""
    pass


class R(V):
    calls = defaultdict(lambda: {"count": 0, "info": {}})

    @classmethod
    def goodbye(cls, instance):
        for s, d in cls.calls.items():
            info = d.get("info", {})
            default_c = "{}.{}()".format(
                info.get("call_modname", "Unknown"),
                info.get("call_funcname", "Unknown"),
            )
            c = info.get("call", default_c)
            instance.writeline("{} called {} times at {}".format(c, d["count"], s))

    def bump(self, count=1):
        s = self.path_value()
        r_class = type(self)
        r_class.calls[s]["count"] += count

    def register(self):
        s = self.path_value()
        r_class = type(self)
        if not r_class.calls:
            # https://docs.python.org/3/library/atexit.html
            atexit.register(r_class.goodbye, instance=self)

        r_class.calls[s]["info"] = self.reflect.info

    def output(self, *args, **kwargs):
        return super().output(*args, **kwargs).strip()

    def __call__(self, *args, **kwargs):
        """Similar to pout.v() but gets rid of name and file information so it can be used
        in loops and stuff, it will print out where the calls came from at the end of
        execution

        this just makes it nicer when you're printing a bunch of stuff each iteration

        :Example:
            for x in range(x):
                pout.r(x)
        """
        kwargs.setdefault("show_path", False)
        super().__call__(*args, **kwargs)
        self.register()
        self.bump()


class VR(R):
    """alias of R"""
    pass


class Sleep(Interface):
    def __call__(self, seconds, **kwargs):
        '''
        same as time.sleep(seconds) but prints out where it was called before sleeping
        and then again after finishing sleeping

        I just find this really handy for debugging sometimes

        since -- 2017-4-27

        :param seconds: float|int, how many seconds to sleep
        '''
        if seconds <= 0.0:
            raise ValueError("Invalid seconds {}".format(seconds))

        self.writeline("Sleeping {} second{} at {}".format(
            seconds,
            "s" if seconds != 1.0 else "",
            self.path_value()
        ))

        time.sleep(seconds)
        self.writelines(["...Done Sleeping", self.path_value(), ""])


class H(Interface):
    '''
    prints "here count"

    example -- 
        h(1) # here 1 (/file:line)
        h() # here line (/file:line)

    count -- integer -- the number you want to put after "here"
    '''
    def body_value(self, count, **kwargs):
        call_info = self.reflect.info
        count = int(count or 0)
        return "here {} ".format(count if count > 0 else call_info['line'])


class B(Interface):
    '''
    create a big text break, you just kind of have to run it and see

    since -- 2013-5-9

    :param *args: mixed, 1-3 arguments
        1 arg = title if string/variable, rows if int
        2 args = title, int
        3 args = title, int, sep
    '''
    def input(self, *args, **kwargs):
        yield None, args

    def body_value(self, args, **kwargs):
        call_info = self.reflect.info

        lines = []

        title = ''
        rows = 1
        sep = '*'

        if len(args) == 1:
            v = Value(args[0])
            if v.typename in set(['STRING', 'BINARY']):
                title = args[0]

            elif v.typename in set(["PRIMITIVE"]):
                arg_name = String(self.reflect.info["args"][0]["name"])
                arg_val = String(self.reflect.info["args"][0]["val"])
                if arg_name == arg_val:
                    rows = int(args[0])
                else:
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
        return "\n".join(lines)


class C(V):
    '''
    kind of like od -c on the command line, basically it dumps each character and info
    about that char

    since -- 2013-5-9

    :param *args: tuple, one or more strings to dump
    '''
    def body_value(self, arg, **kwargs):
        call_info = self.reflect.info
        lines = []
        counter = Counter()
        arg = String(arg)
        counter["total"] = len(arg)

        lines.append('Total Characters: {}'.format(counter['total']))
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

            line.append(repr(c.encode(environ.ENCODING)))

            cint = ord(c)
            if cint > 65535:
                line.append('\\U{:0>8X}'.format(cint))
            else:
                line.append('\\u{:0>4X}'.format(cint))

            if cint < 128:
                counter["ascii"] += 1
            elif cint < 256:
                counter["extended"] += 1
            else:
                counter["unicode"] += 1

            line.append(unicodedata.name(c, 'UNKNOWN'))
            lines.append('\t'.join(line))

        lines.append("Total: {}, Ascii: {}, extended: {}, unicode: {}".format(
            counter['total'],
            counter['ascii'],
            counter['extended'],
            counter['unicode'],
        ))
        lines.append("")
        return "\n".join(lines)


class J(V):
    """
    dump json

    since -- 2013-9-10

    *args -- tuple -- one or more json strings to dump
    """
    def body_value(self, body, **kwargs):
        return super().body_value(json.loads(body), **kwargs)


class M(Interface):
    """
    Print out memory usage at this point in time

    http://docs.python.org/2/library/resource.html
    http://stackoverflow.com/a/15448600/5006
    http://stackoverflow.com/questions/110259/which-python-memory-profiler-is-recommended
    """
    def body_value(self, name, **kwargs):
        if not resource:
            return self._printstr(["UNSUPPORTED OS\n"])

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

        summary = ''
        if name:
            summary += "{}: ".format(name)

        summary += "{0} mb\n".format(round(rss, 2))
        return summary


class E(Interface):
    """Easy exception/error printing

    see e()
    since 5-27-2020

    :Example:
        with pout.e():
            raise ValueError("foo")

    https://github.com/Jaymon/pout/issues/59
    """
    def body_value(self, *args, **kwargs):
        lines = traceback.format_exception(
            self.exc_type,
            self.exc_value,
            self.traceback
        )
        return self._printstr(lines)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.exc_type = exc_type
            self.exc_value = exc_value
            self.traceback = traceback
            self.writeline(self.output())
            reraise(exc_type, exc_value, traceback)

    def __call__(self, **kwargs):
        """
        :returns: context manager
        """
        return self


class P(Interface):
    """this is a context manager for Profiling

    see -- p()
    since -- 10-21-2015
    """

    # profiler p() state is held here
    stack = []

    @classmethod
    def pop(cls, reflect=None):
        instance = cls.stack[-1]
        instance.stop(reflect.info)
        cls.stack.pop(-1)
        return instance

    def start(self, name, call_info, **kwargs):
        self.start = time.time()
        self.name = name
        self.start_call_info = call_info
        self.kwargs = kwargs
        type(self).stack.append(self)

    def stop(self, call_info=None):
        pr_class = type(self)
        name = self.name
        if len(pr_class.stack) > 0:
            found = False
            ds = []
            for d in pr_class.stack:
                if self is d:
                    found = True
                    break

                else:
                    ds.append(d)

            if found and ds:
                name = ' > '.join((d.name for d in ds))
                name += ' > {}'.format(self.name)

        self.stop_call_info = call_info or self.reflect.info
        self.name = name
        self.stop = time.time()
        self.elapsed = self.get_elapsed(self.start, self.stop, 1000.00, 1)
        self.total = "{:.1f} ms".format(self.elapsed)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pr_class = type(self)
        for i in range(len(pr_class.stack)):
            if self is pr_class.stack[i]:
                self.stop()
                pr_class.stack.pop(i)
                break

        self.finish()

    def finish(self):
        self.writeline(self.output(**self.kwargs))

    def body_value(self, *args, **kwargs):
        s = ""
        start_call_info = self.start_call_info
        stop_call_info = self.stop_call_info

        summary = []
        summary.append("{} - {}".format(self.name, self.total))
        summary.append("  start: {} ({}:{})".format(
            self.start,
            self._get_path(start_call_info['file']),
            start_call_info['line']
        ))

        if stop_call_info:
            summary.append("  stop: {} ({}:{})".format(
                self.stop,
                self._get_path(stop_call_info['file']),
                stop_call_info['line']
            ))

        else:
            summary.append("  stop: {}".format(self.stop))

        return "\n".join(summary)

    def get_elapsed(self, start, stop, multiplier, rnd):
        return round(abs(stop - start) * float(multiplier), rnd)

    def __call__(self, name="", **kwargs):
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
        kwargs.setdefault("show_path", False)
        if name:
            self.start(name, self.reflect.info, **kwargs)
            instance = self
        else:
            instance = type(self).pop(self.reflect)
            instance.finish()

        return instance


class L(Interface):
    """Logging context manager used in pout.l()

    This will turn logging to the stderr on for everything inside the with block

    :Example:
        with LoggingInterface():
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

    def __call__(self, logger_name="", level=logging.DEBUG, **kwargs):
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
        self.logger_name = logger_name

        if isinstance(level, basestring):
            self.level = logging._nameToLevel[level.upper()]

        else:
            self.level = level

        return self


class T(Interface):

    call_class = Call

    def body_value(self, *args, **kwargs):
        #call_info = self.reflect.info
        name = kwargs.get("name", "")
        frames = kwargs["frames"]
        inspect_packages = kwargs.get("inspect_packages", False)
        depth = kwargs.get("depth", 0)

        calls = self._get_backtrace(frames=frames, inspect_packages=inspect_packages, depth=depth)
        return "".join(calls)

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

        for index, f in enumerate(frames, 1):
            #prev_f = frames[i]
            #called_module = inspect.getmodule(prev_f[0]).__name__
            #called_func = prev_f[3]

            # https://stackoverflow.com/a/2011168/5006
            called_module = sys.modules[f[0].f_back.f_globals["__name__"]] if f[0].f_back else None
            called_func = f[3]
            call = self.call_class(called_module, called_func, f)
            s = self._get_call_summary(call, inspect_packages=inspect_packages, index=index)
            calls.append(s)

            if depth and (index > depth):
                break

        # reverse the order on return so most recent is on the bottom
        return calls[::-1]

    def _get_call_summary(self, call, index=0, inspect_packages=True):
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
        call_info = call.info
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

    def __call__(self, inspect_packages=False, depth=0, **kwargs):
        '''
        print a backtrace

        since -- 7-6-12

        inpsect_packages -- boolean -- by default, this only prints code of packages that are not 
            in the pythonN directories, that cuts out a lot of the noise, set this to True if you
            want a full stacktrace
        depth -- integer -- how deep you want the stack trace to print (ie, if you only care about
            the last three calls, pass in depth=3 so you only get the last 3 rows of the stack)
        '''
        try:
            frames = inspect.stack()
            kwargs["frames"] = frames[1:]
            kwargs["inspect_packages"] = inspect_packages
            kwargs["depth"] = depth
            super().__call__(**kwargs)

        finally:
            del frames


class Tofile(Interface):
    def __enter__(self):
        self.orig_stream = self.kwargs["pout_module"].stream
        self.kwargs["pout_module"].stream = self.stream
        return self

    def __exit__(self, *args, **kwargs):
        self.kwargs["pout_module"].stream = self.orig_stream

    def __call__(self, path="", **kwargs):
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
            path = os.path.join(os.getcwd(), "{}.txt".format(self.module_name().upper()))

        self.path = path
        self.kwargs = kwargs
        self.stream = FileStream(path)

        return self


class F(Tofile):
    """alias function name of Tofile"""
    pass

