# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import math
import unicodedata
import resource
import platform
import time
import logging
import collections
import re

from .compat import *
from . import environ
from .value import Inspect, Value
from .path import Path
from .utils import String
from .reflect import Call


logger = logging.getLogger(__name__)


class BaseInterface(object):
    """Most of pout's output will go through a child of this class"""

    path_class = Path

    def __init__(self, reflect, stream, **kwargs):
        self.reflect = reflect
        self.stream = stream
        self.kwargs = kwargs

    def __repr__(self):
        return self.full_value()

    def __call__(self):
        s = repr(self)
        self.writeline(s)

    def writeline(self, s):
        self.stream.writeline(s)

    def writelines(self, ss):
        for s in ss:
            self.writeline(s)

    def full_value(self):
        s = self.name_value()
        s += self.path_value()
        s += "\n\n"
        return s

    def name_value(self):
        return self.value()

    def value(self):
        raise NotImplementedError()

    def path_value(self):
        s = ""
        call_info = self.reflect.info
        if call_info:
            s = "({}:{})".format(self._get_path(call_info['file']), call_info['line'])
        return s

    def _get_path(self, path):
        return self.path_class(path)

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
                s = "{} ({}) = {}".format(name, count, self._str_val(val))

            except (TypeError, KeyError, AttributeError) as e:
                logger.warning(e, exc_info=True)
                s = "{} = {}".format(name, self._str_val(val))

        else:
            s = self._str_val(val)

        return s

    def _str_val(self, val):
        '''
        turn val into a string representation of val

        val -- mixed -- the value that will be turned into a string

        return -- string
        '''
        return "{}".format(Value(val))


class InfoInterface(BaseInterface):
    def value(self):
        call_info = self.reflect.info
        pargs = []
        for v in call_info["args"]:
            vt = Value(v['val'])
            full_info = self._str(v['name'], vt.info())
            pargs.append(full_info)

        return self._printstr(pargs)


class ValueInterface(BaseInterface):
    def name_value(self):
        call_info = self.reflect.info
        args = ["{}\n\n".format(self._str(v['name'], v['val'])) for v in call_info['args']]
        return self._printstr(args)

    def value(self):
        call_info = self.reflect.info
        args = ["{}\n\n".format(self._str(None, v['val'])) for v in call_info['args']]
        return self._printstr(args)



class HereInterface(BaseInterface):
    def value(self):
        call_info = self.reflect.info
        count = self.kwargs.get("count", 0)
        #pout2.b()
        #pout2.v(call_info)
        args = ["here {} ".format(count if count > 0 else call_info['line'])]
        return self._printstr(args)


class BreakInterface(BaseInterface):
    def value(self):
        call_info = self.reflect.info
        args = self.kwargs.get("args", [])

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
        return self._printstr(["\n".join(lines)])


class CharInterface(BaseInterface):
    def value(self):
        call_info = self.reflect.info
        args = self.kwargs.get("args", [])
        lines = []
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

                line.append(repr(c.encode(environ.ENCODING)))

                cint = ord(c)
                if cint > 65535:
                    line.append('\\U{:0>8X}'.format(cint))
                else:
                    line.append('\\u{:0>4X}'.format(cint))

                line.append(unicodedata.name(c, 'UNKNOWN'))
                lines.append('\t'.join(line))

            lines.append('')
            lines.append('')

        return self._printstr(["\n".join(lines)])


class JsonInterface(BaseInterface):
    def value(self):
        call_info = self.reflect.info
        args = ["{}\n\n".format(self._str(v['name'], json.loads(v['val']))) for v in call_info['args']]
        return self._printstr(args)


class MemoryInterface(BaseInterface):
    def value(self):
        call_info = self.reflect.info
        name = self.kwargs.get("name", "")
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

        summary += "{0} mb{1}{1}".format(round(rss, 2), "\n")
        calls = [summary]
        return self._printstr(calls)


class ProfileInterface(BaseInterface):
    """this is a context manager for Profiling

    see -- p()
    since -- 10-21-2015
    """

    # profiler p() state is held here
    stack = []

    def __init__(self, reflect, stream, name="", **kwargs):
        super(ProfileInterface, self).__init__(reflect, stream, **kwargs)

        if name:
            self.start(name, reflect.info)
        else:
            self.start_call_info = reflect.info

    @classmethod
    def pop(cls, reflect=None):
        instance = cls.stack[-1]
        instance.stop(reflect.info)
        cls.stack.pop(-1)
        return instance

    def start(self, name, call_info):
        self.start = time.time()
        self.name = name
        self.start_call_info = call_info
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

        self()

    def value(self):
        s = ""
        d = None
        start_call_info = self.start_call_info
        stop_call_info = self.stop_call_info
        d = self.kwargs.get("profiler")

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

        return self._printstr(["\n".join(summary)])

#         if name:
#             d = Profiler(String(name), call_info)
# 
#         else:
#             if len(Profiler.stack) > 0:
#                 d = Profiler.stack[-1]
#                 d.__exit__()
# 
#                 summary = []
#                 summary.append("{} - {}".format(d.name, d.total))
#                 summary.append("  start: {} ({}:{})".format(
#                     d.start,
#                     self._get_path(d.start_call_info['file']),
#                     d.start_call_info['line']
#                 ))
#                 if call_info:
#                     summary.append("  stop: {} ({}:{})".format(
#                         d.stop,
#                         self._get_path(call_info['file']),
#                         call_info['line']
#                     ))
#                     d.stop_call_info = call_info
# 
#                 else:
#                     summary.append("  stop: {}".format(d.stop))
#                     d.stop_call_info = d.start_call_info
# 
#                 calls = ["\n".join(summary)]
#                 s = self._printstr(calls, None)
# 
#         if d:
#             self.profiler = d
# 
#         return s

#     def stop(self, call_info=None):
#         pr_class = type(self)
#         name = self.name
#         if len(pr_class.stack) > 0:
#             found = False
#             ds = []
#             for d in pr_class.stack:
#                 if self is d:
#                     found = True
#                     break
# 
#                 else:
#                     ds.append(d)
# 
#             if found and ds:
#                 name = ' > '.join((d.name for d in pr_class.stack))
#                 name += ' > {}'.format(self.name)
# 
# 
# 
# 
# #             name = ' > '.join((d.name for d in pr_class.stack))
# #             name += ' > {}'.format(self.name)
# 
#         #d = type(self).stack.pop()
#         self.name = name
#         self.stop = time.time()
#         self.elapsed = self.get_elapsed(self.start, self.stop, 1000.00, 1)
#         self.total = "{:.1f} ms".format(self.elapsed)

    def get_elapsed(self, start, stop, multiplier, rnd):
        return round(abs(stop - start) * float(multiplier), rnd)


class LoggingInterface(object):
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


class TraceInterface(BaseInterface):

    call_class = Call

    def value(self):
        #call_info = self.reflect.info
        name = self.kwargs.get("name", "")
        frames = self.kwargs["frames"]
        inspect_packages = self.kwargs.get("inspect_packages", False)
        depth = self.kwargs.get("depth", 0)

        calls = self._get_backtrace(frames=frames, inspect_packages=inspect_packages, depth=depth)
        return self._printstr(calls)

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
        #count = 1

        #for count, f in enumerate(frames[1:], 1):
        for count, f in enumerate(frames, 1):
            #prev_f = frames[i]
            #called_module = inspect.getmodule(prev_f[0]).__name__
            #called_func = prev_f[3]

            call = self.call_class(f)
            s = self._get_call_summary(call, inspect_packages=inspect_packages, index=count)
            calls.append(s)
            #count += 1

            if depth and (count > depth):
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


