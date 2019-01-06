# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import logging

from .compat import String as BaseString, Bytes
from . import environ


class String(BaseString):
    """Small wrapper around string/unicode that guarantees output will be a real
    string ("" in py3 and u"" in py2) and won't fail with a UnicodeException"""
    def __new__(cls, arg):
        '''
        make sure arg is a unicode string

        arg -- mixed -- arg can be anything
        return -- unicode -- a u'' string will always be returned
        '''
        if isinstance(arg, Bytes):
            arg = arg.decode(environ.ENCODING, errors=environ.ENCODING_REPLACE_METHOD)

        else:
            if not isinstance(arg, BaseString):
                arg = BaseString(arg)

        return super(String, cls).__new__(cls, arg)

    def indent(self, indent_count):
        '''
        add whitespace to the beginning of each line of val

        link -- http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/

        val -- string
        indent -- integer -- how much whitespace we want in front of each line of val

        return -- string -- val with more whitespace
        '''
        if indent_count < 1: return self

        s = [("\t" * indent_count) + line for line in self.splitlines(False)]
        s = "\n".join(s)
        return type(self)(s)


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
        logger = logging.getLogger("{}.stderrstream".format(__name__.split(".")[0]))
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
        logger = logging.getLogger("{}.filestream".format(__name__.split(".")[0]))
        if len(logger.handlers) == 0:
            logger.setLevel(logging.DEBUG)
            log_handler = logging.FileHandler(path)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_handler)
            logger.propagate = False

        self.logger = logger

