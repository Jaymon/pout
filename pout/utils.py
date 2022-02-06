# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import logging
import re

from .compat import String as BaseString, Bytes as BaseBytes, is_py2
from . import environ


class StringMixin(object):
    def __format__(self, format_str):
        #pout2.v(format_str)
        return String(self) if isinstance(format_str, BaseString) else Bytes(self)


class String(StringMixin, BaseString):
    """Small wrapper around string/unicode that guarantees output will be a real
    string ("" in py3 and u"" in py2) and won't fail with a UnicodeException"""

    types = (BaseString,)

    def __new__(cls, arg):
        """make sure arg is a unicode string

        :param arg: mixed, arg can be anything
        :returns: unicode, a u"" string will always be returned
        """
        try:
            if isinstance(arg, BaseBytes):
                arg = arg.decode(environ.ENCODING, errors=environ.ENCODING_REPLACE_METHOD)

            else:
                if not isinstance(arg, BaseString):
                    try:
                        arg = BaseString(arg)
                    except TypeError:
                        # this error can happen if arg.__str__() doesn't return
                        # a string, so we call the method directly and go back
                        # through the __new__() flow
                        if hasattr(arg, "__str__"):
                            arg = cls(arg.__str__())

        except RuntimeError as e:
            arg = e

        return super(String, cls).__new__(cls, arg)


    def indent(self, indent_count, indent_string=None):
        '''
        add whitespace to the beginning of each line of val

        link -- http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/

        val -- string
        indent -- integer -- how much whitespace we want in front of each line of val

        return -- string -- val with more whitespace
        '''
        if indent_count < 1: return self

        if indent_string is None:
            indent_string = environ.INDENT_STRING

        s = ((indent_string * indent_count) + line for line in self.splitlines(False))
        s = "\n".join(s)
        return type(self)(s)

    def camelcase(self):
        """Convert a string to use camel case (spaces removed and capital letters)"""
        return "".join(map(lambda s: s.title(), re.split(r"[_-]+", self)))

    def snakecase(self):
        """Convert a string to use snake case (lowercase with underscores in place
        of spaces)"""
        s = []
        prev_ch_was_lower = False

        for i, ch in enumerate(self):
            if ch.isupper():
                if i and prev_ch_was_lower:
                    s.append("_")

                prev_ch_was_lower = False

            else:
                prev_ch_was_lower = True

            s.append(ch)
        return re.sub(r"[\s-]+", "_", "".join(s)).lower()


class Bytes(StringMixin, BaseBytes):

    types = (BaseBytes,)

    def __new__(cls, arg):
        """make sure arg is a byte string

        :param arg: mixed, arg can be anything
        :returns: bytes, a b"" string will always be returned
        """
        try:
            if isinstance(arg, BaseString):
                arg = arg.encode(environ.ENCODING, errors=environ.ENCODING_REPLACE_METHOD)

            else:
                if not isinstance(arg, BaseBytes):
                    arg = BaseBytes(arg)

        except RuntimeError as e:
            arg = e

        return super(Bytes, cls).__new__(cls, arg)


class Stream(object):
    """A Stream object that pout needs to be able to write to something, an instance 
    of some stream instance needs to be set in pout.stream.

    The only interface this object needs is the writeline() function, I thought about
    using an io ABC but that seemed more complicated than it was worth

    https://docs.python.org/3/library/io.html#class-hierarchy
    """
    def writeline(self, s):
        """write out a line and add a newline at the end

        the requirement for the newline is because the children use the logging module
        and it prints a newline at the end by default in 2.7 (you can override it
        in >3.2)

        :param s: string, this will be written to the stream and a newline will be
            added to the end
        """
        raise NotImplementedError()


class StderrStream(Stream):
    """A stream object that writes out to stderr"""
    def __init__(self):
        # this is the pout printing logger, if it hasn't been touched it will be
        # configured to print to stderr, this is what is used in pout_class._print()
        logger = logging.getLogger("stderr.{}".format(__name__.split(".")[0]))
        if len(logger.handlers) == 0:
            logger.setLevel(logging.DEBUG)
            log_handler = logging.StreamHandler(stream=sys.stderr)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_handler)
            logger.propagate = False

        self.logger = logger

    def writeline(self, s):
        self.logger.debug(String(s))


class FileStream(StderrStream):
    """A stream object that writes to a file path passed into it"""
    def __init__(self, path):
        logger = logging.getLogger("file.{}".format(__name__.split(".")[0]))
        if len(logger.handlers) == 0:
            logger.setLevel(logging.DEBUG)
            log_handler = logging.FileHandler(path)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_handler)
            logger.propagate = False

        self.logger = logger


class OrderedItems(object):
    """Returns the items of the wrapped dict in alphabetical/sort order of the keys"""
    def __init__(self, d: dict):
        self.d = d

    def __iter__(self):
        keys = list(self.d.keys())
        keys.sort()
        for k in keys:
            yield k, self.d[k]

